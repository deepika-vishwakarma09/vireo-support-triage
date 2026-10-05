"""Single entry point. Runs the whole pipeline end to end."""
from src import analyse, categorise, charts, clean


def main():
    print("1/4 cleaning data...")
    clean.run()
    print("2/4 categorising tickets (uses cached LLM labels in outputs/ if present)...")
    categorise.run()
    print("3/4 analysing...")
    analyse.run()
    print("4/4 building charts...")
    charts.run()


if __name__ == "__main__":
    main()
