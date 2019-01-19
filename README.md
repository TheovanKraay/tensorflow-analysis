# Python sample for analysing tensorflow recommendation engine tf-recomm <br/>

1. The movies.data and Users.dat files supplied must be in the same directory as the code being run.
2. The TFRecommTester.py program is designed to be run while a Docker container hosting the TF-Recomm engine wrapper created by Andy Cobley is also running (find the wrapper here: https://github.com/acobley/TF-recomm, and find the original source code here: https://hub.docker.com/r/acobley/tfrecomm/).
3. The TFRecommTester.py file should be edited so that the line tn = telnetlib.Telnet("192.168.99.100", 81) refers to the TF-Recomm docker host IP.
4. The TFRecommTester.py program will be quite slow if run as initially configured as it will cycle though all groups of users from similar demographic. 
This takes over an hour! The line "subsetPerms = permutations[(permutations['count'] > 5)]" has been changed to be a
value greater than 5, in order to get a much smaller set of user groups being processed. Code that was run originally had the value set to > 1