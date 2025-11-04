# Welcome to the Group 43 Senior Capstone Project - PIIE

Welcome to Group 43's capstone project. In collaboration with the team members Andrew Grosko, Caleb Muck, Jason Welsh, and Nick Bernloehr, we have created an application that is able to scan and detect single files and files in directories with PII. Please see instructions for below on getting started with the project, either for regular deployment of the application on your desktop, or via development if you would like to play around with the code.

### Setup(Executable) - Windows Only!
--------
1. Within main screen you are at now, locate the **Releases** screen, and then download the latest release with the exe located inside. 

2. Once you are done, click on the exe to install on your Windows Based computer, and then enjoy!



### Setup(Development)
--------
#### Dependency Requirements
1. Make sure you have **Python 3.11.9** installed or later(any version later has not been tested, so use at your own risk!)


#### Installation
____

1. If you would like to contribute to or play around with the code, start by cloning down the repo
```
git clone https://github.com/urboi11/Group-43---Capstone-Project.git
```

2. Once in the project, go to the root of the project directory, and enter the following...
```
python -m venv .venv
```
3. Then in the command line, type the following...
```
python -m pip install briefcase
```
4. If no errors have occurred, then run the following command
```
briefcase dev -r
```
5. The following command above will update the dependencies and then start the project in development mode, which will show the application if no errors have occurred. 


#### TODO: Show project demonstration video? 