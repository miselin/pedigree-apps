
class cronjobs {
  # Reconfigure buildbot master every hour, at thirty minutes past the hour.
  cron { reconfigure_master:
    command => "${::buildbot_path}/bin/python ${::buildbot_path}/bin/buildbot reconfig ${::buildbot_path}/master",
    user    => manager,
    minute  => 30,
  }

  # Update the pedigree-apps repository every hour.
  cron { update_apps_repo:
    command => "cd /home/manager/pedigree-apps && /usr/bin/git pull",
    user    => manager,
    minute  => 0,
  }

  # Update the main Pedigree repository every hour.
  cron { update_main_repo:
    command => "cd /home/manager/pedigree && /usr/bin/git pull",
    user    => manager,
    minute  => 0,
  }

  # Run Puppet every hour.
  cron { puppet:
    command => "/usr/bin/puppet apply /etc/puppet/manifests/site.pp",
    user    => root,
    minute  => 15,
  }
}
