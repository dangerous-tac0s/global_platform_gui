# Global Platform GUI
A quick attempt at GUI wrapper for Global Platform Pro geared towards flexSecure.

Very early.

What do I mean by this? There are zero guard rails on this thing. It will install things 
that need additional configuration (read: FIDO) but they will not work. It doesn't provide 
any user feedback when it's working--such as when it first loads and polls the latest 
releases from the flexSecure repo or when you hit install and it downloads the latest release, 
installs it, and then removes the cap file. 

What has been tested? Not much. I have invested ~2.5 hours in this project so far. All that to
say, anyone is welcome to use it but please keep any frustrations or complaints about its
state at a productive level. Goal #1 is implementing functionality followed by guard rails 
before finally giving the UI some love. Want something soon? Feel free to submit a PR.