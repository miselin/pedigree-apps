#!/usr/bin/env python
'''
    PUP: Pedigree UPdater

    Copyright (c) 2010 Matthew Iselin

    Permission to use, copy, modify, and distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

    pup-install.py: install a package
'''

import os, sys, urllib, sqlite3, tarfile

def main(arglist):

    localPath="./local_repo"
    installRoot="./install_root"
    remotePath="http://theiselins.net/pup"
    
    if localPath[-1] == "/":
        localPath = localPath[0:-1]
    if installRoot[-1] == "/":
        installRoot = installRoot[0:-1]
    if remotePath[-1] == "/":
        remotePath = remotePath[0:-1]

    if not os.path.exists(localPath):
        os.makedirs(localPath)
    if not os.path.exists(installRoot):
        os.makedirs(installRoot)
    
    s = sqlite3.connect(localPath + "/packages.pupdb")
    e = s.execute("select * from packages where name=? order by ver desc limit 1", ([arglist[0]]))
    data = e.fetchone()
    s.close()
    
    # Package name
    packageName = "%s-%s" % (data[1], data[2])
    localFile = "%s/%s.pup" % (localPath, packageName)
    
    print "Preparing to install %s" % (packageName)
    
    if not os.path.exists(localFile):
    
        print "    -> Downloading..."
    
        remoteUrl = "%s/%s.pup" % (remotePath, packageName)
        
        o = urllib.FancyURLopener()
        o.retrieve(remoteUrl, localFile)
    
    print "    -> Installing..."
    
    t = tarfile.open(localFile)
    t.extractall(installRoot)
    
    print "Package %s is now installed." % (packageName)

if __name__ == '__main__':
    main(sys.argv[1:])
