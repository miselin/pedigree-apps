# Apache HTTP Server on Pedigree

The port installs Apache httpd 2.4.68 with the prefork MPM and a small set of
statically linked core modules. Its FHS locations are:

- server: `/usr/sbin/httpd`
- configuration: `/etc/apache2/httpd.conf`
- document root: `/var/www/htdocs`
- logs: `/var/log/apache2`
- runtime state: `/var/run/apache2`

Pedigree does not yet provide working inter-process `fcntl` or `flock` locks.
The shipped configuration caps prefork at one worker, but ordinary prefork
startup still creates a parent and child. Use the supported single-process
development mode:

```sh
/usr/sbin/httpd -X -f /etc/apache2/httpd.conf
```

Do not run the server without `-X`, or raise `ServerLimit` or
`MaxRequestWorkers` above one, until target file locking works. The server uses
numeric UID and GID 65534 because the base image does not currently provide a
`daemon` account. TLS, CGI, DSOs, and optional database-backed modules are
outside this initial target port.
