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

    pup-sync.py: sync the local database with a remote repository
'''

import os, sys, urllib, sqlite3

def main(arglist):

    localPath="./local_repo"
    remotePath="http://theiselins.net/pup"
    
    if remotePath[-1] == "/":
        remotePath = remotePath[0:-1]
    if localPath[-1] == "/":
        localPath = localPath[0:-1]

    if not os.path.exists(localPath):
        os.makedirs(localPath)
    
    o = urllib.FancyURLopener()
    o.retrieve(remotePath + "/packages.pupdb", localPath + "/packages_new.pupdb")
    
    # If the database isn't a valid sqlite database, this will fail
    s = sqlite3.connect(localPath + "/packages_new.pupdb")
    e = s.execute("select * from packages")
    s.close()
    
    os.rename(localPath + "/packages_new.pupdb", localPath + "/packages.pupdb")
    
    print "Synchronisation complete."

if __name__ == '__main__':
    main(sys.argv[1:])
