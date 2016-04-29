FROM ubuntu
MAINTAINER github/miselin

RUN apt-get update
RUN apt-get install -y python-pip

# Don't use dash, use bash. This is crucial for e.g. libtool.
RUN echo "dash dash/sh boolean false" | debconf-set-selections
RUN DEBIAN_FRONTEND=noninteractive dpkg-reconfigure dash

WORKDIR /tmp
ADD requirements.txt /tmp/requirements.txt
ADD install_deps_debian.sh /tmp/install_deps_debian.sh
ADD pup /tmp/pup

RUN pip install -r ./requirements.txt
RUN bash ./install_deps_debian.sh

RUN pip install -q --upgrade /tmp/pup

# Volumes we'll expose to the container when we run a build. Most of these are
# to be read-only.
VOLUME /cross /pedigree_src /pedigree_apps /download /patches /package_repo

WORKDIR /

CMD /bin/true
