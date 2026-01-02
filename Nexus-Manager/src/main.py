if __name__ == "__main__":
    # Add the src directory to the path so imports work when running directly
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))

    from cli import main
    main()