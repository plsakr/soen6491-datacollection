import os
from tqdm import tqdm
import sqlite3
import subprocess
import json

repo_name = input('repo name? ')
repo_path = input('relative repo path? ')
db_path = input('relative db path? ')
smells_path = input('smells path? ')
directory_containing_organic = input('directory containing organic? (. if in same directory) ')

# print all directory information
print(f'repo_name: {repo_name}')
print(f'repo_path: {repo_path}')
print(f'db_path: {db_path}')
print(f'smells_path: {smells_path}')
print(f'directory_containing_organic: {directory_containing_organic}')

current_path = os.getcwd()
print(f'current path: {current_path}')

input('Press enter to continue')

# Connect to the database
conn = sqlite3.connect(db_path)

# get commits from database

c = conn.cursor()
commits = c.execute('SELECT DISTINCT commit_hash FROM Refactoring').fetchall()
previous_commits = c.execute('SELECT DISTINCT commit_hash, previous_commit FROM Commits WHERE previous_commit IS NOT NULL AND commit_hash IN (SELECT DISTINCT commit_hash FROM Refactoring)').fetchall()
commits = [commit[0]for commit in commits]
previous_commits = [(commit[0], commit[1]) for commit in previous_commits]
previous_commits = dict(previous_commits)

all_commits = set(commits + list(previous_commits.values()))

print(f'Found {len(commits)} refactoring commits')
print(f'Found {len(previous_commits)} previous commits')
print(f'Total commits: {len(commits) + len(previous_commits)}')
print(f'Found {len(all_commits)} unique commits')

print('Missing commits:')
def get_missing_commits():
    missing_commits = []
    for commit in all_commits:
        if not os.path.exists(f'{smells_path}/{repo_name}-{commit}.json'):
            missing_commits.append(commit)
    return missing_commits

missing_commits = get_missing_commits()
attempted_fixes = 0
previous_missing_commits = len(missing_commits)
while len(missing_commits) > 0 and attempted_fixes < 10:

    print(f'{len(missing_commits)} MISSING COMMITS, ATTEMPTING TO FIX')

    for missing_commit in tqdm(missing_commits):
        os.chdir(repo_path)
        subprocess.run(['git', 'checkout', missing_commit, '--force'])
        os.chdir(current_path)

        subprocess.run(["java", "-jar", f"{directory_containing_organic}/organic-v0.1.1-OPT.jar", "-sf", f"{smells_path}/{repo_name}-{missing_commit}.json", "-src", f"{repo_path}"])
        

    missing_commits = get_missing_commits()
    attempted_fixes += 1
    if len(missing_commits) == previous_missing_commits:
        print('Could not fix missing commits')
        break
    else:
        previous_missing_commits = len(missing_commits)

print('Final missing commits:')
missing_commits = get_missing_commits()
if len(missing_commits) > 0:
    print(missing_commits, 'still missing. SOMETHING WENT WRONG. exiting now.')
    exit()

print('All commits found, recreating smells and metrics tables')

def get_code_smells(json_file, filename):
    # Load the JSON file
    with open(json_file) as f:
        data = json.load(f)

    # Initialize a list to store the code smells
    code_smells = []

    did_find_data = False
    # Iterate over the data
    for item in data:
        # Check if the file name is in the list
        if filename in item['sourceFile']['fileRelativePath']:
            did_find_data = True
            # Iterate over the smells
            for smell in item['smells']:
                # Append the smell name and file path to the list
                code_smells.append((smell['name'], item['sourceFile']['fileRelativePath']))
                

        # Iterate over the methods
        for method in item['methods']:
            # Check if the method has 'smells' key
            if 'smells' in method:
                # Check if the file name is in the list
                if filename in item['sourceFile']['fileRelativePath']:
                    did_find_data = True
                    # Iterate over the smells
                    for smell in method['smells']:
                        # Append the smell name and file path to the list
                        code_smells.append((smell['name'], item['sourceFile']['fileRelativePath']))
                        

    if not did_find_data:
        print(f'Could not find data for {filename} in commit {json_file.split("-")[-1].split(".")[0]}')
        # input('Press enter to continue')

    return code_smells

def get_code_metrics(json_file, filename):
    # Load the JSON file
    with open(json_file) as f:
        data = json.load(f)

    # Initialize a list to store the code metrics
    code_metrics = []


    # Iterate over the data
    did_find_data = False
    for item in data:
        # Check if the file name is in the list
        if filename in item['sourceFile']['fileRelativePath']:
            # Iterate over the metrics
            for metric, value in item['metricsValues'].items():
                # Append the metric type, method name, and value to the list
                code_metrics.append((metric, item['sourceFile']['fileRelativePath'], value, None))
                did_find_data = True

        # Iterate over the methods
        for method in item['methods']:
            # Check if the method has 'metrics' key
            if 'metricsValues' in method:
                # Check if the file name is in the list
                if filename in item['sourceFile']['fileRelativePath']:
                    # Iterate over the metrics
                    for metric, value in method['metricsValues'].items():
                        # Append the metric type, method name, and value to the list
                        code_metrics.append((metric, item['sourceFile']['fileRelativePath'], value, method['fullyQualifiedName'].split('.')[-1]))
                        did_find_data = True
    
    if not did_find_data:
        print(f'Could not find data for {filename} in commit {json_file.split("-")[-1].split(".")[0]}')
        # input('Press enter to continue')

    return code_metrics

def get_files_in_refactoring(commit_hash):
    # Get the files that were refactored in the commit
    refactored_files = c.execute('SELECT DISTINCT commit_hash, fileId, path FROM Refactoring JOIN RefactoredFile RF on Refactoring.id = RF.refactoringId JOIN File F on F.id = RF.fileId WHERE commit_hash = ?', (commit_hash,)).fetchall()

    # Return the list of files
    return [(file[1], file[2]) for file in refactored_files]

def insert_smell(smell):
    c.execute('INSERT INTO OrganicSmell (file, commit_hash, smell) VALUES (?, ?, ?)', smell)

def insert_metric(metric):
    c.execute('INSERT INTO OrganicMetric (metric_type, file, method_name, value, commit_hash) VALUES (?, ?, ?, ?, ?)', metric)

c.execute('DELETE From OrganicSmell')
c.execute('DELETE From OrganicMetric')
# smell type: {fileId: nbr, commit_hash: commit_hash, smell: string}

for hash in tqdm(commits):
    refactored_files = get_files_in_refactoring(hash)

    previous_hash = previous_commits[hash] if hash in previous_commits else None

    for file in refactored_files:
        smells_current = get_code_smells(f'{smells_path}/{repo_name}-{hash}.json', file[1])
        smells_current = list(map(lambda x: (file[0], hash, x[0]), smells_current))
        metrics_current = get_code_metrics(f'{smells_path}/{repo_name}-{hash}.json', file[1])
        metrics_current = list(map(lambda x: (x[0], file[0], x[3], x[2], hash), metrics_current))
        

        for smell in smells_current:
            insert_smell(smell)

        for metric in metrics_current:
            insert_metric(metric)

        if previous_hash:
            smells_previous = get_code_smells(f'{smells_path}/{repo_name}-{previous_hash}.json', file[1])
            smells_previous = list(map(lambda x: (file[0], previous_hash, x[0]), smells_previous))
            metrics_previous = get_code_metrics(f'{smells_path}/{repo_name}-{previous_hash}.json', file[1])
            metrics_previous = list(map(lambda x: (x[0], file[0], x[3], x[2], previous_hash), metrics_previous))
            
            for smell in smells_previous:
                insert_smell(smell)

            for metric in metrics_previous:
                insert_metric(metric)




conn.commit()
conn.close()