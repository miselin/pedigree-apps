
class packages {
  # supervisord package (for managing buildbots).
  package { 'supervisor':
    ensure => latest,
  }

  # buildbot package (for buildbot masters).
  package { 'buildbot':
    ensure => latest,
  }

  # buildbot package (for buildbot slaves).
  package { 'buildbot-slave':
    ensure => latest,
  }
}
