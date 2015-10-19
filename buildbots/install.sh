#!/bin/bash

old=$(pwd)
script_dir=$(cd -P -- "$(dirname -- "$0")" && pwd -P) && script_dir=$script_dir
cd $old

set -e

sudo cp -r $script_dir/puppet /etc/
sudo cp -r $script_dir/puppet /etc/

# Trigger an immediate Puppet run to apply the new configuration.
sudo puppet apply /etc/puppet/manifests/site.pp
