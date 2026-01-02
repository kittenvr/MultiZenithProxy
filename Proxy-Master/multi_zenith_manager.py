
import os
import json
import shutil
import subprocess
import threading
import time
import uuid
import socket
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse
import sys
import signal
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_zenith_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ZenithInstance:
    
    def __init__(self, instance_id: str, config: dict):
        self.instance_id = instance_id
        self.config = config
        self.process = None
        self.status = "stopped"
        self.start_time = None
        self.connection_time = None
        self.last_rotation_time = None
        self.queue_position = None
        self.last_queue_update = None
        
        self.instance_dir = os.path.join("instances", instance_id)
        os.makedirs(self.instance_dir, exist_ok=True)
        
        self._copy_template_files()
        
        self._initialize_instance_config()
    
    def _copy_template_files(self):
        template_dir = "template"
        if os.path.exists(template_dir):
            for item in os.listdir(template_dir):
                src = os.path.join(template_dir, item)
                dst = os.path.join(self.instance_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        else:
            logger.warning(f"Template directory not found for instance {self.instance_id}")
    
    def _initialize_instance_config(self):
        launch_config = {
            "auto_update": self.config.get("auto_update", True),
            "auto_update_launcher": self.config.get("auto_update_launcher", True),
            "release_channel": self.config.get("release_channel", "java.1.21.4"),
            "version": self.config.get("version", "0.0.0"),
            "local_version": self.config.get("local_version", "0.0.0"),
            "repo_owner": self.config.get("repo_owner", "rfresh2"),
            "repo_name": self.config.get("repo_name", "ZenithProxy"),
        }
        
        if "custom_jvm_args" in self.config:
            launch_config["custom_jvm_args"] = self.config["custom_jvm_args"]
        
        with open(os.path.join(self.instance_dir, "launch_config.json"), "w") as f:
            json.dump(launch_config, f, indent=2)
        
        config_dir = os.path.join(self.instance_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
    
    def start(self):
        if self.status != "stopped":
            logger.warning(f"Instance {self.instance_id} is already running or starting")
            return False
        
        self.status = "starting"
        self.start_time = datetime.now()
        
        try:
            original_cwd = os.getcwd()
            os.chdir(self.instance_dir)
            
            release_channel = self.config.get("release_channel", "java.1.21.4")
            
            if release_channel.startswith("java"):
                cmd = ["python", "-m", "launcher.launcher"]
            elif release_channel.startswith("linux"):
                cmd = ["./ZenithProxy"]
            else:
                cmd = ["python", "-m", "launcher.launcher"]
            
            logger.info(f"Starting instance {self.instance_id} with command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid
            )
            
            self._start_monitoring()
            
            self.status = "running"
            logger.info(f"Instance {self.instance_id} started successfully")
            
            os.chdir(original_cwd)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start instance {self.instance_id}: {e}")
            self.status = "stopped"
            os.chdir(original_cwd)
            return False
    
    def _start_monitoring(self):
        threading.Thread(target=self._monitor_output, daemon=True).start()
        threading.Thread(target=self._monitor_status, daemon=True).start()
    
    def _monitor_output(self):
        """Monitor process output"""
        if not self.process:
            return
        
        try:
            while self.status == "running":
                if self.process.stdout:
                    line = self.process.stdout.readline()
                    if line:
                        logger.info(f"[{self.instance_id}] {line.strip()}")
                        self._parse_output_line(line)
                
                if self.process.stderr:
                    line = self.process.stderr.readline()
                    if line:
                        logger.error(f"[{self.instance_id}] {line.strip()}")
                
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error monitoring output for {self.instance_id}: {e}")
    
    def _parse_output_line(self, line: str):
        """Parse output lines for important information"""
        line_lower = line.lower()
        
        if "connected to server" in line_lower:
            self.connection_time = datetime.now()
            self.status = "connected"
            logger.info(f"Instance {self.instance_id} connected to server")
        
        elif "disconnected" in line_lower or "kicked" in line_lower:
            if self.status == "connected":
                self.status = "disconnected"
                logger.info(f"Instance {self.instance_id} disconnected from server")
        
        elif "queue" in line_lower and "position" in line_lower:
            try:
                parts = line.split(":")
                if len(parts) > 1:
                    position_str = parts[-1].strip()
                    position = int(position_str)
                    self.queue_position = position
                    self.last_queue_update = datetime.now()
                    logger.info(f"Instance {self.instance_id} queue position: {position}")
            except (ValueError, IndexError, AttributeError):
                pass
        
        elif "estimated time" in line_lower or "eta" in line_lower:
            try:
                if "minutes" in line_lower:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit() and i > 0 and "minutes" in parts[i+1].lower():
                            eta_minutes = int(part)
                            self.queue_eta = eta_minutes * 60
                            logger.info(f"Instance {self.instance_id} queue ETA: {eta_minutes} minutes")
                            break
            except (ValueError, IndexError, AttributeError):
                pass
    
    def _monitor_status(self):
        """Monitor instance status and handle timeouts"""
        while self.status == "running":
            time.sleep(5)
            
            if self.process and self.process.poll() is not None:
                self.status = "stopped"
                logger.info(f"Instance {self.instance_id} process terminated")
                break
    
    def stop(self):
        """Stop the ZenithProxy instance"""
        if self.status == "stopped":
            logger.warning(f"Instance {self.instance_id} is already stopped")
            return False
        
        self.status = "stopping"
        logger.info(f"Stopping instance {self.instance_id}")
        
        try:
            if self.process:
                if hasattr(self, '_send_command'):
                    self._send_command("shutdown")
                    time.sleep(3)
                
                if self.process.poll() is None:
                    if os.name == 'posix':
                        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                    else:
                        self.process.terminate()
                    
                    time.sleep(2)
                    
                    if self.process.poll() is None:
                        self.process.kill()
            
            self.status = "stopped"
            self.process = None
            logger.info(f"Instance {self.instance_id} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping instance {self.instance_id}: {e}")
            self.status = "stopped"
            self.process = None
            return False
    
    def restart(self):
        """Restart the ZenithProxy instance"""
        if self.stop():
            return self.start()
        return False
    
    def _send_command(self, command: str):
        """Send command to ZenithProxy instance via HTTP API if available, or stdin if not"""
        logger.info(f"Sending command to {self.instance_id}: {command}")
        
        http_api_port = self.config.get("http_api_port")
        if http_api_port:
            try:
                url = f"http://localhost:{http_api_port}/api/command"
                response = requests.post(url, json={"command": command}, timeout=2)
                if response.status_code == 200:
                    logger.info(f"Command sent successfully to {self.instance_id} via HTTP API")
                    return True
                else:
                    logger.warning(f"HTTP API failed for {self.instance_id}: {response.status_code}, trying stdin")
            except Exception as e:
                logger.warning(f"HTTP API error for {self.instance_id}: {e}, trying stdin")
        
        if self.process and self.process.poll() is None:
            try:
                if self.process.stdin:
                    self.process.stdin.write(f"{command}\n")
                    self.process.stdin.flush()
                    logger.info(f"Command sent to {self.instance_id} via stdin")
                    return True
                else:
                    logger.warning(f"Cannot send command to {self.instance_id}: no stdin available")
            except Exception as e:
                logger.error(f"Error sending command to {self.instance_id} via stdin: {e}")
        else:
            logger.warning(f"Cannot send command to {self.instance_id}: process not running")
        
        return False
    
    def get_status(self) -> dict:
        """Get current status of the instance"""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        connection_duration = None
        if self.connection_time:
            connection_duration = (datetime.now() - self.connection_time).total_seconds()
        
        time_until_kick = None
        if self.status == "connected" and self.connection_time:
            time_until_kick = self.estimate_time_until_kick()
        
        queue_eta = None
        if hasattr(self, 'queue_eta') and self.queue_eta:
            queue_eta = self.queue_eta
        elif self.queue_position:
            queue_eta = self.get_queue_eta()
        
        return {
            "instance_id": self.instance_id,
            "status": self.status,
            "uptime": uptime,
            "connection_duration": connection_duration,
            "time_until_kick": time_until_kick,
            "queue_position": self.queue_position,
            "queue_eta": queue_eta,
            "last_queue_update": self.last_queue_update.isoformat() if self.last_queue_update else None,
            "config": {
                "account": self.config.get("account", ""),
                "proxy": self.config.get("proxy", ""),
                "server": self.config.get("server", "")
            }
        }
    
    def is_ready_for_rotation(self) -> bool:
        """Check if instance is ready for rotation"""
        if self.status != "connected":
            return False
        
        if self.connection_time:
            connected_duration = datetime.now() - self.connection_time
            return connected_duration.total_seconds() > 4.5 * 3600
        
        return False
    
    def estimate_time_until_kick(self) -> Optional[int]:
        """Estimate seconds until this account will be kicked by session limit"""
        if self.status != "connected" or not self.connection_time:
            return None
        
        connected_duration = datetime.now() - self.connection_time
        time_until_kick = self.session_limit - connected_duration.total_seconds()
        
        buffer_multiplier = 1.0
        if connected_duration.total_seconds() > 3 * 3600:
            buffer_multiplier = 1.5
        if connected_duration.total_seconds() > 4 * 3600:
            buffer_multiplier = 2.0
            
        safe_buffer = self.rotation_buffer * buffer_multiplier
        time_until_kick = max(0, time_until_kick - safe_buffer)
        
        return int(time_until_kick) if time_until_kick > 0 else 0
    
    def get_queue_eta(self) -> Optional[int]:
        """Get estimated queue wait time in seconds"""
        if hasattr(self, 'queue_eta') and self.queue_eta:
            uncertainty_buffer = int(self.queue_eta * 0.5)
            min_buffer = 300
            max_buffer = 3600
            
            safe_eta = self.queue_eta + max(min_buffer, min(uncertainty_buffer, max_buffer))
            return safe_eta
        
        if self.queue_position and self.queue_position > 0:
            estimated_eta = self.queue_position * 120
            
            uncertainty_buffer = int(estimated_eta * 0.75)
            estimated_eta = min(estimated_eta + uncertainty_buffer, 24 * 3600)
            
            return estimated_eta
        
        return None
    
    def should_connect_for_rotation(self) -> bool:
        """Determine if this instance should connect to prepare for rotation"""
        if self.status == "connected":
            return False
        
        if self.status not in ["starting", "in_queue", "connecting"]:
            return True
        
        queue_eta = self.get_queue_eta()
        if queue_eta and queue_eta <= 3600:
            return False
        
        return True

class MultiZenithManager:
    """Manages multiple ZenithProxy instances"""
    
    def __init__(self, config_file: str = "multi_zenith_config.json"):
        self.config_file = config_file
        self.instances: Dict[str, ZenithInstance] = {}
        self.rotation_enabled = False
        self.rotation_strategy = "sequential"
        self.rotation_interval = 300
        self.current_active_instance = None
        self.next_rotation_time = None
        self.queue_eta_cache = {}
        self.session_limit = 5 * 3600
        self.rotation_buffer = 300
        self.last_queue_check = None
        self.proxy_pool = []
        self._proxy_index = 0
        
        self.load_config()
        
        if self.rotation_enabled:
            self._start_rotation_monitor()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                
                self.rotation_enabled = config.get("rotation_enabled", False)
                self.rotation_strategy = config.get("rotation_strategy", "sequential")
                self.rotation_interval = config.get("rotation_interval", 300)
                
                self.proxy_pool = config.get("proxy_pool", [])
                
                instances_config = config.get("instances", {})
                for instance_id, instance_config in instances_config.items():
                    self.add_instance(instance_id, instance_config, load_only=True)
                
                logger.info(f"Loaded configuration from {self.config_file}")
            else:
                logger.info(f"No config file found, creating default")
                self.save_config()
        
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                "rotation_enabled": self.rotation_enabled,
                "rotation_strategy": self.rotation_strategy,
                "rotation_interval": self.rotation_interval,
                "proxy_pool": self.proxy_pool,
                "instances": {}
            }
            
            for instance_id, instance in self.instances.items():
                config["instances"][instance_id] = instance.config
            
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Configuration saved to {self.config_file}")
        
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def add_instance(self, instance_id: str, config: dict, load_only: bool = False) -> bool:
        """Add a new ZenithProxy instance"""
        if instance_id in self.instances:
            logger.warning(f"Instance {instance_id} already exists")
            return False
        
        if not config.get('proxy') and self.proxy_pool:
            config['proxy'] = self._get_next_proxy()
            logger.info(f"Assigned proxy {config['proxy']} to instance {instance_id}")
        
        if not self._validate_instance_config(config):
            logger.error(f"Invalid configuration for instance {instance_id}")
            return False
        
        instance = ZenithInstance(instance_id, config)
        self.instances[instance_id] = instance
        
        if not load_only:
            self.save_config()
        
        logger.info(f"Added instance {instance_id}")
        return True
    
    def _validate_instance_config(self, config: dict) -> bool:
        """Validate instance configuration"""
        required_fields = ["account", "server"]
        
        for field in required_fields:
            if field not in config or not config[field]:
                logger.error(f"Missing required field: {field}")
                return False
        
        return True
    
    def remove_instance(self, instance_id: str) -> bool:
        """Remove a ZenithProxy instance"""
        if instance_id not in self.instances:
            logger.warning(f"Instance {instance_id} does not exist")
            return False
        
        instance = self.instances[instance_id]
        
        if instance.status != "stopped":
            instance.stop()
        
        instance_dir = instance.instance_dir
        if os.path.exists(instance_dir):
            shutil.rmtree(instance_dir)
        
        del self.instances[instance_id]
        self.save_config()
        
        logger.info(f"Removed instance {instance_id}")
        return True
    
    def start_instance(self, instance_id: str) -> bool:
        """Start a specific instance"""
        if instance_id not in self.instances:
            logger.error(f"Instance {instance_id} does not exist")
            return False
        
        instance = self.instances[instance_id]
        return instance.start()
    
    def stop_instance(self, instance_id: str) -> bool:
        """Stop a specific instance"""
        if instance_id not in self.instances:
            logger.error(f"Instance {instance_id} does not exist")
            return False
        
        instance = self.instances[instance_id]
        return instance.stop()
    
    def restart_instance(self, instance_id: str) -> bool:
        """Restart a specific instance"""
        if instance_id not in self.instances:
            logger.error(f"Instance {instance_id} does not exist")
            return False
        
        instance = self.instances[instance_id]
        return instance.restart()
    
    def start_all_instances(self):
        """Start all instances"""
        for instance_id, instance in self.instances.items():
            if instance.status == "stopped":
                instance.start()
    
    def stop_all_instances(self):
        """Stop all instances"""
        for instance_id, instance in self.instances.items():
            if instance.status != "stopped":
                instance.stop()
    
    def get_instance_status(self, instance_id: str) -> Optional[dict]:
        """Get status of a specific instance"""
        if instance_id not in self.instances:
            return None
        
        return self.instances[instance_id].get_status()
    
    def get_all_statuses(self) -> List[dict]:
        """Get status of all instances"""
        return [instance.get_status() for instance in self.instances.values()]
    
    def enable_rotation(self, strategy: str = "sequential", interval: int = 300):
        """Enable account rotation"""
        self.rotation_enabled = True
        self.rotation_strategy = strategy
        self.rotation_interval = interval
        self.save_config()
        
        self._start_rotation_monitor()
        
        logger.info(f"Rotation enabled with strategy: {strategy}, interval: {interval}s")
    
    def disable_rotation(self):
        """Disable account rotation"""
        self.rotation_enabled = False
        self.save_config()
        logger.info("Rotation disabled")
    
    def _start_rotation_monitor(self):
        """Start the rotation monitoring thread"""
        if not self.rotation_enabled:
            return
        
        def rotation_monitor():
            while self.rotation_enabled:
                try:
                    self._check_and_rotate()
                    time.sleep(self.rotation_interval)
                except Exception as e:
                    logger.error(f"Error in rotation monitor: {e}")
                    time.sleep(60)
        
        threading.Thread(target=rotation_monitor, daemon=True).start()
        logger.info("Rotation monitor started")
    
    def _check_and_rotate(self):
        """Check if rotation is needed and perform rotation"""
        if not self.rotation_enabled:
            return
        
        logger.info("Checking for rotation opportunities...")
        
        ready_instances = []
        for instance_id, instance in self.instances.items():
            if instance.is_ready_for_rotation():
                ready_instances.append(instance_id)
        
        if not ready_instances:
            self._check_and_prepare_instances()
            return
        
        if self.rotation_strategy == "sequential":
            current_index = -1
            if self.current_active_instance and self.current_active_instance in ready_instances:
                current_index = ready_instances.index(self.current_active_instance)
            
            next_index = (current_index + 1) % len(ready_instances)
            next_instance_id = ready_instances[next_index]
            
        elif self.rotation_strategy == "random":
            import random
            next_instance_id = random.choice(ready_instances)
        
        else:
            next_instance_id = ready_instances[0]
        
        next_instance = self.instances[next_instance_id]
        current_instance = None
        if self.current_active_instance:
            current_instance = self.instances[self.current_active_instance]
        
        if current_instance and next_instance:
            current_time_until_kick = current_instance.estimate_time_until_kick()
            next_queue_eta = next_instance.get_queue_eta()
            
            if current_time_until_kick and next_queue_eta:
                optimal_connect_time = current_time_until_kick - next_queue_eta
                
                logger.info(f"Rotation timing calculation:")
                logger.info(f"  Current instance will be kicked in: {current_time_until_kick // 60} minutes")
                logger.info(f"  Next instance queue ETA: {next_queue_eta // 60} minutes")
                logger.info(f"  Optimal connect time: {optimal_connect_time // 60} minutes from now")
                
                if optimal_connect_time <= 0:
                    logger.info("Connecting next instance now to be ready for rotation")
                    next_instance._send_command("connect")
                    
                    if current_time_until_kick > 0:
                        logger.info(f"Scheduling rotation in {current_time_until_kick // 60} minutes")
                        time.sleep(10)
                        self._perform_rotation(next_instance_id)
                        return
        
        self._perform_rotation(next_instance_id)
    
    def _check_and_prepare_instances(self):
        """Check if any instances should be prepared for future rotation"""
        logger.info("Checking if instances need preparation for future rotation...")
        
        current_instance = None
        if self.current_active_instance:
            current_instance = self.instances[self.current_active_instance]
        
        if current_instance and current_instance.status == "connected":
            time_until_kick = current_instance.estimate_time_until_kick()
            if time_until_kick and time_until_kick > 0:
                logger.info(f"Current instance will be kicked in {time_until_kick // 60} minutes")
                
                candidates = []
                
                for instance_id, instance in self.instances.items():
                    if instance_id == self.current_active_instance:
                        continue
                    
                    if instance.status == "connected":
                        score = 1000
                    elif instance.status in ["starting", "in_queue", "connecting"]:
                        queue_eta = instance.get_queue_eta()
                        if queue_eta:
                            score = max(0, 100 - (queue_eta // 60))
                        else:
                            score = 50
                    else:
                        score = 10
                    
                    queue_eta = instance.get_queue_eta()
                    if queue_eta and queue_eta > 3600:
                        score = max(1, score - (queue_eta // 3600))
                    
                    candidates.append((instance_id, instance, score))
                
                candidates.sort(key=lambda x: x[2], reverse=True)
                
                num_in_queue = sum(1 for _, instance, _ in candidates 
                                  if instance.status in ["starting", "in_queue", "connecting"])
                num_connected = sum(1 for _, instance, _ in candidates 
                                   if instance.status == "connected")
                
                logger.info(f"Queue strategy analysis:")
                logger.info(f"  Total candidates: {len(candidates)}")
                logger.info(f"  Already connected: {num_connected}")
                logger.info(f"  Currently in queue: {num_in_queue}")
                
                target_in_queue = min(3, max(2, len(candidates) // 3))
                
                accounts_to_prepare = []
                accounts_to_keep_in_queue = []
                
                for instance_id, instance, score in candidates:
                    if instance.status in ["starting", "in_queue", "connecting"]:
                        if num_in_queue <= target_in_queue:
                            accounts_to_keep_in_queue.append((instance_id, instance, score))
                            num_in_queue -= 1
                        else:
                            accounts_to_prepare.append((instance_id, instance, score))
                    elif instance.status == "connected":
                        accounts_to_keep_in_queue.append((instance_id, instance, score))
                    else:
                        accounts_to_prepare.append((instance_id, instance, score))
                
                accounts_to_prepare.sort(key=lambda x: x[2], reverse=True)
                
                num_to_prepare = max(0, target_in_queue - (len(accounts_to_keep_in_queue) + num_in_queue))
                
                logger.info(f"Queue strategy decision:")
                logger.info(f"  Target accounts in queue: {target_in_queue}")
                logger.info(f"  Will keep {len(accounts_to_keep_in_queue)} accounts as-is")
                logger.info(f"  Will prepare {min(num_to_prepare, len(accounts_to_prepare))} additional accounts")
                
                num_to_prepare = min(num_to_prepare, len(accounts_to_prepare))
                
                for instance_id, instance, score in accounts_to_keep_in_queue:
                    if instance.status == "connected":
                        logger.info(f"Instance {instance_id} is already connected and ready for rotation")
                    else:
                        logger.info(f"Instance {instance_id} is in queue (position: {getattr(instance, 'queue_position', 'unknown')}, "
                                   f"ETA: {instance.get_queue_eta() // 60 if instance.get_queue_eta() else 'unknown'} minutes) - keeping in queue")
                
                prepared_count = 0
                for instance_id, instance, score in accounts_to_prepare:
                    if prepared_count >= num_to_prepare:
                        break
                    
                    queue_eta = instance.get_queue_eta()
                    
                    if queue_eta and queue_eta <= time_until_kick:
                        safety_margin = max(300, int(queue_eta * 0.3))
                        if queue_eta + safety_margin <= time_until_kick:
                            logger.info(f"Preparing instance {instance_id} for rotation (ETA: {queue_eta // 60} minutes, safety margin: {safety_margin // 60} minutes)")
                            instance._send_command("connect")
                            prepared_count += 1
                        else:
                            logger.info(f"Instance {instance_id} queue time ({queue_eta // 60} minutes) with safety margin ({safety_margin // 60} minutes) "
                                       f"exceeds time until kick ({time_until_kick // 60} minutes). Not connecting yet.")
                    elif queue_eta:
                        logger.info(f"Instance {instance_id} has long queue time ({queue_eta // 60} minutes), "
                                   f"longer than time until kick ({time_until_kick // 60} minutes)")
                    else:
                        if prepared_count < num_to_prepare:
                            logger.info(f"Instance {instance_id} has unknown queue time. "
                                       f"Connecting to establish queue position and get ETA.")
                            instance._send_command("connect")
                            prepared_count += 1
                
                total_ready = len(accounts_to_keep_in_queue) + prepared_count
                logger.info(f"Queue strategy summary:")
                logger.info(f"  Accounts ready/prepared: {total_ready}")
                logger.info(f"  Accounts in queue: {len(accounts_to_keep_in_queue)}")
                logger.info(f"  Accounts being prepared: {prepared_count}")
                logger.info(f"  Total accounts ready for rotation: {total_ready}")
                
                all_long_queue = True
                for instance_id, instance, _ in candidates:
                    queue_eta = instance.get_queue_eta()
                    if instance.status == "connected":
                        all_long_queue = False
                        break
                    elif queue_eta and queue_eta <= 3600:
                        all_long_queue = False
                        break
                
                if all_long_queue and total_ready == 0:
                    logger.warning("⚠️ CRITICAL: All accounts have long queue times!")
                    logger.warning("⚠️ Strategy: Connect ALL disconnected accounts to establish queue positions")
                    logger.warning("⚠️ This will help get accurate ETA and find shortest queue")
                    
                    for instance_id, instance, _ in candidates:
                        if instance.status not in ["connected", "in_queue", "connecting", "starting"]:
                            logger.info(f"Connecting {instance_id} to establish queue position")
                            instance._send_command("connect")
                
                if prepared_count == 0:
                    logger.info("No suitable instances found for preparation")
        else:
            logger.info("No current active instance or instance not connected")
    
    def _perform_rotation(self, next_instance_id: str):
        """Perform the actual rotation to the specified instance"""
        logger.info(f"Performing rotation to instance {next_instance_id}")
        
        next_instance = self.instances[next_instance_id]
        
        if self.current_active_instance and self.current_active_instance != next_instance_id:
            current_instance = self.instances[self.current_active_instance]
            logger.info(f"Disconnecting current instance {self.current_active_instance}")
            
            if hasattr(current_instance, '_send_command'):
                current_instance._send_command("disconnect")
            
            time.sleep(10)
        
        logger.info(f"Connecting next instance {next_instance_id}")
        
        if hasattr(next_instance, '_send_command'):
            next_instance._send_command("connect")
        
        self.current_active_instance = next_instance_id
        self.next_rotation_time = datetime.now() + timedelta(hours=4)
        
        logger.info(f"Rotation complete. Next rotation scheduled for {self.next_rotation_time}")
    
    def send_command_to_instance(self, instance_id: str, command: str) -> bool:
        """Send a command to a specific instance"""
        if instance_id not in self.instances:
            logger.error(f"Instance {instance_id} does not exist")
            return False
        
        instance = self.instances[instance_id]
        return instance._send_command(command)
    
    def send_command_to_all(self, command: str):
        """Send a command to all instances"""
        results = {}
        for instance_id, instance in self.instances.items():
            results[instance_id] = instance._send_command(command)
        return results
    
    def create_template_from_instance(self, instance_id: str, template_name: str = "template"):
        """Create a template from an existing instance"""
        if instance_id not in self.instances:
            logger.error(f"Instance {instance_id} does not exist")
            return False
        
        instance = self.instances[instance_id]
        template_dir = template_name
        
        if os.path.exists(template_dir):
            shutil.rmtree(template_dir)
        
        shutil.copytree(instance.instance_dir, template_dir)
        
        logger.info(f"Created template {template_name} from instance {instance_id}")
        return True

class CLIInterface:
    """Command-line interface for the Multi-Zenith Manager"""
    
    def __init__(self, manager: MultiZenithManager):
        self.manager = manager
        self.running = True
    
    def run(self):
        """Run the CLI interface"""
        print("Multi-ZenithProxy Manager")
        print("Type 'help' for available commands")
        
        while self.running:
            try:
                cmd_input = input("> ").strip()
                if not cmd_input:
                    continue
                
                self._process_command(cmd_input)
            
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                logger.error(f"Error: {e}")
    
    def _process_command(self, cmd_input: str):
        """Process a command"""
        parts = cmd_input.split()
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1:]
        
        try:
            if command == "help":
                self._show_help()
            
            elif command == "exit":
                self.running = False
                print("Goodbye!")
            
            elif command == "status":
                self._show_status()
            
            elif command == "add":
                self._add_instance(args)
            
            elif command == "remove":
                self._remove_instance(args)
            
            elif command == "start":
                self._start_instance(args)
            
            elif command == "stop":
                self._stop_instance(args)
            
            elif command == "restart":
                self._restart_instance(args)
            
            elif command == "startall":
                self._start_all()
            
            elif command == "stopall":
                self._stop_all()
            
            elif command == "rotation":
                self._handle_rotation(args)
            
            elif command == "command":
                self._send_command(args)
            
            elif command == "template":
                self._handle_template(args)
            
            else:
                print(f"Unknown command: {command}")
        
        except Exception as e:
            logger.error(f"Error processing command: {e}")
    
    def _show_help(self):
        """Show help information"""
        help_text = """
Available Commands:
  help                    Show this help message
  exit                    Exit the manager
  status                  Show status of all instances
  add <id> <config>      Add a new instance
  remove <id>             Remove an instance
  start <id>              Start an instance
  stop <id>               Stop an instance
  restart <id>            Restart an instance
  startall                Start all instances
  stopall                 Stop all instances
  rotation <on/off>      Enable/disable rotation
  command <id> <cmd>     Send command to instance
  template <create>       Create template from instance
"""
        print(help_text)
    
    def _show_status(self):
        """Show status of all instances"""
        statuses = self.manager.get_all_statuses()
        
        if not statuses:
            print("No instances configured")
            return
        
        print("Instance Status:")
        print("-" * 80)
        
        for status in statuses:
            instance_id = status["instance_id"]
            instance_status = status["status"]
            uptime = status["uptime"]
            connection_duration = status["connection_duration"]
            time_until_kick = status["time_until_kick"]
            queue_position = status["queue_position"]
            queue_eta = status["queue_eta"]
            account = status["config"]["account"]
            server = status["config"]["server"]
            
            uptime_str = self._format_duration(uptime) if uptime else "N/A"
            connection_str = self._format_duration(connection_duration) if connection_duration else "N/A"
            time_until_kick_str = self._format_duration(time_until_kick) if time_until_kick else "N/A"
            queue_eta_str = self._format_duration(queue_eta) if queue_eta else "N/A"
            
            print(f"ID: {instance_id}")
            print(f"  Status: {instance_status}")
            print(f"  Account: {account}")
            print(f"  Server: {server}")
            print(f"  Uptime: {uptime_str}")
            print(f"  Connected: {connection_str}")
            print(f"  Time until kick: {time_until_kick_str}")
            if queue_position:
                print(f"  Queue Position: {queue_position}")
            if queue_eta and queue_eta > 0:
                print(f"  Queue ETA: {queue_eta_str}")
            print()
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human-readable format"""
        if seconds is None:
            return "N/A"
        
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"
    
    def _add_instance(self, args: List[str]):
        """Add a new instance"""
        if len(args) < 2:
            print("Usage: add <id> <config_file>")
            return
        
        instance_id = args[0]
        config_file = args[1]
        
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            
            if self.manager.add_instance(instance_id, config):
                print(f"Instance {instance_id} added successfully")
            else:
                print(f"Failed to add instance {instance_id}")
        
        except Exception as e:
            print(f"Error adding instance: {e}")
    
    def _remove_instance(self, args: List[str]):
        """Remove an instance"""
        if len(args) < 1:
            print("Usage: remove <id>")
            return
        
        instance_id = args[0]
        
        if self.manager.remove_instance(instance_id):
            print(f"Instance {instance_id} removed successfully")
        else:
            print(f"Failed to remove instance {instance_id}")
    
    def _start_instance(self, args: List[str]):
        """Start an instance"""
        if len(args) < 1:
            print("Usage: start <id>")
            return
        
        instance_id = args[0]
        
        if self.manager.start_instance(instance_id):
            print(f"Instance {instance_id} started successfully")
        else:
            print(f"Failed to start instance {instance_id}")
    
    def _stop_instance(self, args: List[str]):
        """Stop an instance"""
        if len(args) < 1:
            print("Usage: stop <id>")
            return
        
        instance_id = args[0]
        
        if self.manager.stop_instance(instance_id):
            print(f"Instance {instance_id} stopped successfully")
        else:
            print(f"Failed to stop instance {instance_id}")
    
    def _restart_instance(self, args: List[str]):
        """Restart an instance"""
        if len(args) < 1:
            print("Usage: restart <id>")
            return
        
        instance_id = args[0]
        
        if self.manager.restart_instance(instance_id):
            print(f"Instance {instance_id} restarted successfully")
        else:
            print(f"Failed to restart instance {instance_id}")
    
    def _start_all(self):
        """Start all instances"""
        self.manager.start_all_instances()
        print("All instances started")
    
    def _stop_all(self):
        """Stop all instances"""
        self.manager.stop_all_instances()
        print("All instances stopped")
    
    def _handle_rotation(self, args: List[str]):
        """Handle rotation commands"""
        if len(args) < 1:
            print("Usage: rotation <on/off> [strategy] [interval]")
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "on":
            strategy = args[1] if len(args) > 1 else "sequential"
            interval = int(args[2]) if len(args) > 2 else 300
            self.manager.enable_rotation(strategy, interval)
            print(f"Rotation enabled with strategy: {strategy}, interval: {interval}s")
        
        elif subcommand == "off":
            self.manager.disable_rotation()
            print("Rotation disabled")
        
        else:
            print("Usage: rotation <on/off> [strategy] [interval]")
    
    def _send_command(self, args: List[str]):
        """Send command to instance"""
        if len(args) < 2:
            print("Usage: command <id> <command>")
            return
        
        instance_id = args[0]
        command = " ".join(args[1:])
        
        if self.manager.send_command_to_instance(instance_id, command):
            print(f"Command sent to {instance_id}")
        else:
            print(f"Failed to send command to {instance_id}")
    
    def _handle_template(self, args: List[str]):
        """Handle template commands"""
        if len(args) < 2:
            print("Usage: template create <instance_id> [template_name]")
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "create":
            instance_id = args[1]
            template_name = args[2] if len(args) > 2 else "template"
            
            if self.manager.create_template_from_instance(instance_id, template_name):
                print(f"Template {template_name} created from instance {instance_id}")
            else:
                print(f"Failed to create template from instance {instance_id}")
        
        else:
            print("Usage: template create <instance_id> [template_name]")

    def _get_next_proxy(self):
        """Get next proxy from pool (round-robin)"""
        if not self.proxy_pool:
            return None
        proxy = self.proxy_pool[self._proxy_index]
        self._proxy_index = (self._proxy_index + 1) % len(self.proxy_pool)
        return proxy


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Multi-ZenithProxy Manager")
    parser.add_argument("--config", default="multi_zenith_config.json", help="Configuration file")
    args = parser.parse_args()
    
    manager = MultiZenithManager(args.config)
    
    cli = CLIInterface(manager)
    cli.run()

if __name__ == "__main__":
    main()
