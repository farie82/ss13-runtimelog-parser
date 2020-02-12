# SS13 Runtime Parser
A python based parser that parses the runtime log and makes github issues per runtime

## Installation requirements
You'll need the 'pygithub' package to run this script.
`pip install pygithub`

## Configuration
Make sure that you have a filled out config file in the config directory. An example is found in the config/example directory.
The example config is configured for the ParadiseStation SS13 server.

## Running
To run the program simply start a command line and type:
`py ./runtime_parses.py [relative_path_to_runtime_file]
The file will default to runtime.log in the directory where the script is located.