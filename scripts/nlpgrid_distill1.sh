#$ -N andrz-distill1
#$ -o /nlp/data/andrz/logs/distill1.stdout
#$ -e /nlp/data/andrz/logs/distill1.stderr
#$ -wd /nlp/data/andrz/avrae-dataset
#$ -pe parallel-onenode 60
#$ -l h_vmem=16G
/nlp/data/andrz/avrae-dataset/venv/bin/python distill1.py
