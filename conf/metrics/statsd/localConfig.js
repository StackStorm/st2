// Sample statsd config for usage with metrics instrumentation
{
  // IP and port of a local or remote graphite instance to which statsd will
  // submit metrics
  graphiteHost: "127.0.0.1",
  graphitePort: 2003,

  // statsd listen IP and port
  address: "0.0.0.0",
  port: 8125,

  // Enable debug mode for easier debugging, disable in production
  debug: true,

  // Disable legacy name prefix
  graphite: {
    legacyNamespace: false
  }
}
