import sqlite3
import os
import subprocess
from tqdm import tqdm

repo_name = input('Enter the name of the repository: ')

repo_path = f'tmp/{repo_name}'

new_repo_path = input(f'Enter the path of the repository (default: {repo_path}, leave blank to keep): ')

if new_repo_path != '':
    repo_path = new_repo_path

db_file = input('Enter the name of the sqlite db file (default: refactoring.db):')

if db_file == '':
    db_file = 'refactoring.db'

current_dir = os.getcwd()
tool_path = f'{current_dir}/pmd/bin/pmd'

print('Detected tool path:', tool_path)

# open the sqlite db file
conn = sqlite3.connect(db_file)

# get all commits in db
commits = list(map(lambda x: x[0], conn.execute('SELECT commit_hash FROM Commits').fetchall()))

print('Creating new table')
# create a new table to store the duplicates

conn.execute('CREATE TABLE IF NOT EXISTS Duplicates (commit_hash TEXT, duplicate_size INTEGER, FOREIGN KEY(commit_hash) REFERENCES Commits(commit_hash))')

os.chdir(repo_path)
# for each commit, checkout the commit and run the script
for commit in tqdm(commits):
    print(f'Checking out commit {commit}')
    # checkout the commit
    subprocess.run(['git', 'checkout', commit, '--force'])

    # run the script
    csv = subprocess.run([tool_path, 'cpd', '--minimum-tokens', '100', '--dir', '.', '--language', 'java', '--format', 'csv'], capture_output=True).stdout.decode('utf-8').strip()

    # parse the data
    duplicates = csv.split('\n')[1:]
    total_duplicate_lines = 0
    for duplicate in duplicates:
        duplicate_data = duplicate.split(',')
        total_duplicate_lines += int(duplicate_data[0])

    print(f'Commit {commit} has {len(duplicates)} duplicates with {total_duplicate_lines} lines')
    c = conn.cursor()
    c.execute('INSERT INTO Duplicates (commit_hash, duplicate_size) VALUES (?, ?)', (commit, total_duplicate_lines))
    conn.commit()

print('DONE')
conn.close()
