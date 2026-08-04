from poc4.database import get_engine


def main():
    engine1 = get_engine()
    engine2 = get_engine()

    print("engine1 id:", id(engine1))
    print("engine2 id:", id(engine2))

    print(
        "same object:",
        engine1 is engine2
    )


if __name__ == "__main__":
    main()