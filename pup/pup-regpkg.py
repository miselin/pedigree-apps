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

    pip-regpkg: register a package within a given repository
'''

import os, sys
from optparse import OptionParser
import hashlib
import sqlite3

def main(arglist):
    optParser = OptionParser(usage="%prog --repo REPO_PATH --name NAME --ver VERSION [--deps LIST_OF_DEPS]",
                             version="pimp-regpkg 0.1")
    optParser.add_option("--repo", dest="repoBase", help="""
        Path to the directory containing the local package repository. This will be
        where the new package will be created in. The package database should be in
        this directory (but use pimp-regpkg to register this package in the
        database.""".replace("    ", "").strip())
    optParser.add_option("--deps", dest="depsList", help="""
        Space-separated list of packages the package being registered depends on.
        These packages do not need to exist in the repository yet.""".replace("    ", "").strip())
    optParser.add_option("--name", dest="packageName", help="""
        The name of the package being registered.""".replace("    ", "").strip())
    optParser.add_option("--ver", dest="packageVersion", help="""
        The version of the package being registered.""".replace("    ", "").strip())

    (options, args) = optParser.parse_args(arglist)

    if options.repoBase == None:
        print "You must specify a path to the repository via the --repo option."
        exit()

    repoBase = options.repoBase
    if not (repoBase[-1] == "/" or repoBase[-1] == "\\"):
        repoBase += "/"

    if options.packageName == None:
        print "You must specify a name for the package via the --name option."
        exit()
    elif options.packageVersion == None:
        print "You must specify a version for the package via the --ver option."
        exit()

    packageName = options.packageName
    packageVersion = options.packageVersion

    deps = []
    if options.depsList <> None:
        deps = filter(lambda x: len(x) > 0, options.depsList.split(" "))

    # Hash the package
    packagePath = repoBase + packageName + "-" + packageVersion + ".pup"
    if not os.path.exists(packagePath):
        print "Can't find the pimp for this package!"
        exit()

    fileHash = 0
    with open(packagePath, "rb") as f:
        fileHash = hashlib.sha1(f.read()).hexdigest()

    # Install into the database
    alreadyExisted = os.path.exists(repoBase + "packages.pupdb")
    db = sqlite3.connect(repoBase + "packages.pupdb")

    if not alreadyExisted:
        db.execute("""create table packages (
                      pkid integer primary key autoincrement,
                      name text(256),
                      ver text(64),
                      deps text(4096),
                      sha1 text(42)
                      )""")

    # Using a tuple here performs proper sanitisation of input strings to avoid SQL
    # injection attacks (which would be fairly nasty!)
    db.execute("delete from packages where name=? and ver=?", (packageName, packageVersion))
    db.execute("insert into packages (name, ver, deps, sha1) values (?, ?, ?, ?)", (packageName, packageVersion, " ".join(deps), fileHash))

    # By now everything seems to have fun fine, commit the changes to the database
    db.commit()

    db.close()

    print "Package '" + packageName + "-" + packageVersion + "' has now been registered."

if __name__ == '__main__':
    main(sys.argv[1:])

