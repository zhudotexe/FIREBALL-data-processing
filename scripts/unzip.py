"""Given a path to an instance dir, unzip the files and merge them into a single .jsonl file."""
import pathlib
import sys

sys.path.append("..")
from dataset import utils


def main():
    path = pathlib.Path(sys.argv[-1])
    if not path.is_dir():
        print("You must specify the path to an instance dir")
        return
    instance_id = path.stem
    with open(path / f"{instance_id}.jsonl", "wb") as f:
        for line in utils.combat_dir_iterator_raw(path):
            f.write(line)


if __name__ == "__main__":
    main()
