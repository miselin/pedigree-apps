
class config {
  file { 'buildbot master.cfg':
    name   => "${::buildbot_path}/master/master.cfg",
    source => "puppet:///modules/${module_name}/master.cfg",
    mode   => "0644",
    owner  => "manager",
    group  => "manager",
  }

  file { '/etc/supervisor/conf.d/buildbots.conf':
    source  => "puppet:///modules/${module_name}/etc/supervisor/conf.d/buildbots.conf",
    mode    => "0644",
    owner   => "manager",
    group   => "manager",
    require => [Package['supervisor']],
  }
}
