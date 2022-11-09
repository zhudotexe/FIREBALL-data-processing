#$ -N andrz-distill2
#$ -o /nlp/data/andrz/logs/distill2.stdout
#$ -e /nlp/data/andrz/logs/distill2.stderr
#$ -wd /nlp/data/andrz/avrae-dataset
#$ -pe parallel-onenode 60
#$ -l h_vmem=16G
source /nlp/data/andrz/avrae-dataset/venv/bin/activate
/nlp/data/andrz/avrae-dataset/venv/bin/python distill2.py
