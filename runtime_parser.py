# Need PyGithub
import sys
import re
from github import Github
from datetime import datetime

# Used to dynamically get issues (workaround for the 1000 issue retrieve limit)
ISSUES_SINCE = datetime.strptime("01-01-2020", "%d-%m-%Y")

class Parser:
    def load_config(self):
        try:
            with open('./config/config.txt', 'r') as f:
                for line in f:
                    self.parse_config(line)
        except Exception as e:
            print("Failed to load the config file, error: {0}".format(e))

    def parse_config(self, text):
        text = text.lstrip() # Keep the spacing on the right

        if(len(text) <= 1 or text[1] == '#'):
            return
        match = re.search(r'(.*?) (.*)', text)
        var = match.group(1).upper()
        value = match.group(2)
        if var == 'FIND_PREF_WARNING_CKEY_RE':
            self.FIND_PREF_WARNING_CKEY_RE = value
        elif var == 'FIND_USR_CKEY_RE':
            self.FIND_USR_CKEY_RE = value
        elif var == 'FIND_PARAM_CKEY_RE':
            self.FIND_PARAM_CKEY_RE = value
        elif var == 'FIND_REF_BASED_CKEY_RE':
            self.FIND_REF_BASED_CKEY_RE = value
        elif var == 'REPO_PATH':
            self.REPO_PATH = value
        elif var == 'BOT_NAME':
            self.BOT_NAME = value
        elif var == 'TOKEN':
            self.TOKEN = value
        elif var == 'ISSUE_LABELS':
            self.ISSUE_LABELS = value.split(',')
        elif var == 'REOPEN_COMMENT_BASE':
            self.REOPEN_COMMENT_BASE = value.replace("\\n", "\n")
        elif var == 'RUNTIME_RE':
            self.RUNTIME_RE = value
        elif var == 'PROC_NAME_RE':
            self.PROC_NAME_RE = value

    def parse_file(self, fileName):
        try:
            with open(fileName, "r") as f:
                text = f.read()
                return self.parse_text(text)
        except Exception as e:
            print("File could not be read, filename = {0}. With error: {1}".format(fileName, e))

    def parse_text(self, text):
        results = {}
        match_iter = re.finditer(self.RUNTIME_RE, text)
        done = False
        try:
            match = match_iter.__next__()
        except StopIteration:
            # empty file? No runtimes?!
            return
        next_match = None
        while not done:
            start = match.start()
            try:
                next_match = match_iter.__next__()
                end_index = next_match.start()-1
            except StopIteration:
                #EOF
                end_index = len(text)-1
                done = True
            
            runtime_title = "[RUNTIME] " + match.group(1)
            body = text[start:end_index]
            
            proc_match = re.search(self.PROC_NAME_RE, body)
            if(proc_match is not None):
                runtime_title += " proc: " + proc_match.group(1)
            if(runtime_title not in results):
                body = self.censor_text(body)
                results[runtime_title] = self.runtime(runtime_title, body)
            match = next_match
        return results

    def censor_text(self, text):
        result = re.sub(self.FIND_PREF_WARNING_CKEY_RE, r'\1CKEY\2', text)
        result = re.sub(self.FIND_USR_CKEY_RE, r'\1CKEY\2', result)
        result = re.sub(self.FIND_PARAM_CKEY_RE, r'\1CKEY\2', result)
        result = re.sub(self.FIND_REF_BASED_CKEY_RE, r'\1CKEY\2CKEY\3', result)
        return result

    def generate_and_make_github_issues(self, results):
        g = Github(self.TOKEN)
        repo = g.get_repo(self.REPO_PATH)
        #open_issues = repo.get_issues(state='open', labels=ISSUE_LABELS, creator=BOT_NAME)
        for issue in IssuesQuery(repo, ISSUES_SINCE, 'open', self.ISSUE_LABELS, self.BOT_NAME):
            if(issue.title in results):
                del results[issue.title]
        #old_issues = repo.get_issues(state='closed', labels=ISSUE_LABELS, creator=BOT_NAME)
        for old_issue in IssuesQuery(repo, ISSUES_SINCE, 'closed', self.ISSUE_LABELS, self.BOT_NAME):
            if(old_issue.title in results):
                old_issue.edit(state='open')
                print("reopened: " + old_issue.title)
                old_issue.create_comment(self.REOPEN_COMMENT_BASE + results[old_issue.title].body)
                del results[old_issue.title]
        for key in results:
            runt = results[key]
            self.make_github_issue(repo, runt.runtime_title, runt.body, self.ISSUE_LABELS)
            print("opened: " + runt.runtime_title)
        
    def make_github_issue(self, repo, title, body=None, labels=None):
        repo.create_issue(title = title, body = body, labels = labels)

    class runtime:
        def __init__(self, runtime_title, body):
            self.runtime_title = runtime_title
            self.body = '```\n' + body +'\n```'

#https://github.com/PyGithub/PyGithub/issues/824
class IssuesQuery:
    def __init__(self, repo, since, state, labels, creator):
        self.repo = repo
        self.since = since
        self.state = state
        self.creator = creator
        self.labels = labels
        self.issues = self.__query(since)
        self.last_number = 0
    
    def __iter__(self):
        while True:
            results = False
            for issue in self.issues:
                if issue.number > self.last_number:
                    results = True
                    yield issue
            
            # If no more results then stop iterating.
            if not results:
                break
            # Start new query picking up where we left off. Previous issue will be first one returned, so skip it.
            self.last_number = issue.number
            self.issues = self.__query(issue.created_at)
        
    def __query(self, since):
        return self.repo.get_issues(since = since, state = self.state, creator = self.creator, labels = self.labels, sort="created", direction="asc")

if len(sys.argv) > 1:
    fileName = sys.argv[1]
    print(fileName)
else:
    fileName = "runtime.log"
    print("Filename defaulted to" + fileName)
parser = Parser()
parser.load_config()
result = parser.parse_file(fileName)

if(result is not None):
    print("Total unique runtimes: " + str(len(result)))
    parser.generate_and_make_github_issues(result)
else:
    print("No runtimes found")