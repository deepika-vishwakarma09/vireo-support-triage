
"""Single entry point. Runs the whole pipeline end to end."""
from src import clean
# from src import categorise, analyse, charts   # added in the next steps


def main():
    print("1/4 cleaning data...")
    clean.run()
    print("2/4 categorising tickets...   (not built yet)")
    print("3/4 analysing...              (not built yet)")
    print("4/4 building charts...        (not built yet)")


if __name__ == "__main__":
    main()