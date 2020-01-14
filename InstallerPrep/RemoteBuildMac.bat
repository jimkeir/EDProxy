set VERSION=2.4.3
set SSH_CRED=jimkeir@macmini

"C:\Program Files\Git\usr\bin\ssh.exe" %SSH_CRED% "cd ~/EDProxy && rm -f *.dmg && git pull && PATH=$PATH:~/Library/Python/2.7/bin:/usr/local/bin ./macosx-pyinstall.sh --version %VERSION%"
"C:\Program Files\Git\usr\bin\scp.exe" -p %SSH_CRED%:~/EDProxy/edproxy-macosx-%VERSION%.dmg ..\Release\
