# Dynatrace SMS Notification Plugin

## Plugin Intro

The **Dynatrace SMS Notification Plugin** is a custom Dynatrace Python extension that monitors Dynatrace problems and sends SMS notifications based on configurable severity and escalation rules.

The plugin:

- Polls Dynatrace for active and recently closed problems.
- Supports filtering problems by Management Zones.
- Sends SMS notifications for newly detected problems.
- Supports **L1, L2, and L3 escalation levels**.
- Escalates notifications based on configurable time thresholds.
- Optionally handles `SYNTHETIC_TEST` and `HTTP_CHECK` problems with a dedicated payload and delay-only escalation.
- Sends cumulative notifications when a problem is closed.
- Maintains separate local caches for standard and synthetic problems.
- Supports **dry-run mode** for testing without sending SMS.
- Publishes custom metrics for processing time, processed problems, SMS activity, and execution health.

If no Management Zone is configured, the plugin treats the configuration as applying to **all Management Zones**.

---

## Architecture

```text
                    ┌──────────────────────────┐
                    │       Dynatrace          │
                    │     Problem API          │
                    └────────────┬─────────────┘
                                 │
                                 │ Fetch Problems
                                 ▼
                    ┌──────────────────────────┐
                    │   DynatraceClient        │
                    │                          │
                    │ Problem retrieval &      │
                    │ Management Zone filtering│
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       SmsEngine          │
                    │                          │
                    │ Problem processing       │
                    │ Escalation handling      │
                    │ Notification handling    │
                    └───────┬───────────┬──────┘
                            │           │
                 ┌──────────┘           └──────────┐
                 ▼                                 ▼
       ┌──────────────────┐              ┌──────────────────┐
       │  CacheManager    │              │   SmsClient      │
       │                  │              │                  │
       │ Problem state    │              │ SMS API          │
       │ Escalation state │              │ communication    │
       └────────┬─────────┘              └────────┬─────────┘
                │                                 │
                ▼                                 ▼
       problem_cache.json                    SMS Gateway
       synthetic_problem_cache.json
```

### Main Components

| Component | Responsibility |
|---|---|
| `main.py` | Extension lifecycle, initialization and polling |
| `DynatraceClient` | Retrieves problems from Dynatrace |
| `SmsEngine` | Processes problems and controls notification/escalation flow |
| `SmsClient` | Communicates with the external SMS API |
| `SmsFormatter` | Builds SMS message content |
| `CacheManager` | Maintains problem and escalation state |
| `escalation.py` | Determines initial/current escalation level |
| `validator.py` | Validates extension configuration |
| `MetricsPublisher` | Publishes plugin health and processing metrics |
| `logger.py` | Provides console and Dynatrace logging |

### Notification Flow

For a new problem:

```text
Problem detected
      │
      ▼
Determine initial escalation level
      │
      ├── L1 severity → L1 notification
      ├── L2 severity → L2 notification
      └── L3 severity → L3 notification
      │
      ▼
Send SMS
      │
      ▼
Store problem state in cache
```

Synthetic problems always begin at L1 and do not use problem severity. When synthetic handling is disabled,
`SYNTHETIC_TEST` and `HTTP_CHECK` problems are ignored. When enabled, synthetic problems use either the standard
recipients and delays or their own dedicated recipients and delays.

For an existing problem:

```text
Existing problem
      │
      ▼
Calculate elapsed time
      │
      ├── L2 threshold reached → L2 escalation
      │
      └── L3 threshold reached → L3 escalation
      │
      ▼
Send SMS
      │
      ▼
Update cache
```

For a closed problem:

```text
Problem closed
      │
      ▼
Read cached escalation level
      │
      ▼
Send cumulative closure notifications
      │
      ▼
Mark problem CLOSED in cache
```

---

## Prerequisites

### Dynatrace

- Dynatrace environment with permission to install/configure extensions.
- Dynatrace **ActiveGate** capable of running Python extensions.
- Python runtime supported by the extension.

The extension configuration specifies:

```yaml
python:
  runtime:
    module: dt_sms_plugin
    version:
      min: "3.10"
```

The project setup currently requires:

```text
Python >= 3.14
```

Therefore, the deployment environment must provide the Python runtime required by the packaged extension.

### Dynatrace API Access

The plugin requires:

- Dynatrace tenant URL.
- Dynatrace API token.

The token must provide the permissions required by the plugin to retrieve Dynatrace problems.

### SMS API

The external SMS API must be reachable from the ActiveGate hosting the extension.

The configuration requires:

- SMS API URL.
- SMS API username.
- SMS API password.
- SMS API timeout.

The current SMS client expects an HTTP POST request using:

```text
Content-Type: application/x-www-form-urlencoded
```

The request contains the `auth` and `jsonString` form parameters.

### Network Connectivity

The ActiveGate must be able to reach:

```text
Dynatrace → Dynatrace API
ActiveGate → SMS API
```

Verify firewall, proxy and routing requirements before deployment.

---

## Installation / Deployment

### 1. Build the Extension

From the project root, build the extension package using the Dynatrace Extensions SDK tooling.

Ensure the version in:

```text
extension/extension.yaml
```

matches the version being deployed.

Example:

```yaml
name: custom:dt-sms-plugin
version: 1.0.12
```

The Python package version is derived from `extension/extension.yaml`.

### 2. Validate the Extension

Before deployment, validate the extension package and activation schema using the Dynatrace Extensions SDK CLI.

Resolve any schema, packaging or dependency errors before deploying to Dynatrace.

### 3. Deploy the Extension

Deploy the generated extension package to the target Dynatrace environment.

The extension is configured as a Python extension:

```yaml
python:
  runtime:
    module: dt_sms_plugin
```

After deployment, create a monitoring configuration for the extension.

### 4. Configure the Extension

Configure the following areas.

#### Polling

Set:

- Polling interval.
- Lookback window.
- Maximum problems per execution, if required.

#### Dynatrace

Provide:

- Dynatrace URL.
- Dynatrace API token.

#### Management Zones

Specify the Management Zones to monitor.

If the Management Zone list is left empty:

```text
[]
```

the plugin treats this as **all Management Zones**.

#### Escalation

Configure:

- L1 recipients.
- L1 severities.
- L2 recipients.
- L2 severities.
- L3 recipients.
- L3 severities.
- L2 escalation delay.
- L3 escalation delay.

The configuration validator requires:

```text
L2 delay < L3 delay
```

Open notifications include their current escalation level in the status, for example `OPEN L1`. Closed
notifications contain only `CLOSED`.

#### Synthetic Problems

Synthetic SMS handling is disabled by default. When enabled, problems containing an affected entity of type
`SYNTHETIC_TEST` or `HTTP_CHECK` use the synthetic payload.

Select **Use Same Escalation Settings** to reuse the standard L1/L2/L3 recipients and L2/L3 delays. Standard
severity selections are not applied to synthetic problems. If the option is cleared, configure dedicated
synthetic recipients and delays.

Synthetic payloads use the matching affected entity name as the flow name and the
`dt.synthetic.step.name` evidence property as the incident name.

#### SMS API

Configure:

- SMS API URL.
- Username.
- Password.
- Timeout.

The current SMS client sends form-encoded parameters:

```text
auth
jsonString
```

and uses the required SMS gateway session cookie when configured.

#### Dry Run

Enable dry-run mode when testing the extension without actually sending SMS messages.

### 5. Verify Deployment

After configuration, check the extension status in Dynatrace.

The extension should successfully complete initialization and begin executing its polling cycle.

Expected logs include:

```text
Initializing DT SMS Plugin...
Initialization completed.
Query started.
```

Successful processing should produce a message similar to:

```text
Processed <number> problems in <time> ms.
```

---

## Troubleshooting

### Extension fails during initialization

Check the extension logs for:

```text
Error running self.initialize
```

and the associated Python exception.

Common causes include:

- Invalid activation configuration.
- Missing required configuration values.
- Incorrect activation-schema property names.
- Invalid Dynatrace credentials.
- Invalid SMS API configuration.

The plugin validates settings during initialization, so configuration errors will prevent the extension from starting.

### `KeyError` during initialization

Example:

```text
KeyError('dynatraceUrl')
```

This indicates that the code is attempting to read a configuration key that is not present at the location expected by the implementation.

Verify that the activation schema, generated configuration and `load_settings()` implementation use the same property names and hierarchy.

Do not assume the key exists simply because it is present in the schema—inspect the actual `activation_config` structure if necessary.

### Management Zone configuration is empty

An empty Management Zone configuration is intentional.

The plugin supports:

```text
management_zones = []
```

as the equivalent of monitoring all Management Zones.

Ensure that the Dynatrace problem query does not unintentionally reject an empty Management Zone list.

### SMS API returns HTTP 406

Example:

```text
406 Client Error: Not Acceptable
```

Check the HTTP request generated by `SmsClient`.

The current SMS API expects:

```text
Content-Type: application/x-www-form-urlencoded
```

Do **not** automatically add:

```text
Accept: application/json
```

if the target SMS API does not accept that header.

Also verify that the required session cookie is included when required by the SMS gateway.

For example:

```text
Cookie: JSESSIONID=<value>
```

Compare the Python request with a known-working `curl` request.

### SMS API works with curl but not with the plugin

This is usually caused by a difference between the two HTTP requests.

Compare:

- HTTP method.
- URL.
- `Content-Type`.
- `Accept` header.
- Cookies.
- Form parameters.
- JSON encoding.
- Authentication values.
- Recipient value.
- Request timeout.

The plugin should reproduce the working `curl` request as closely as possible.

Enable payload/request logging temporarily when troubleshooting, while ensuring that passwords, tokens and other credentials are not exposed in logs.

### SMS response needs to be inspected

Add response logging around:

```python
response = self._session.post(...)
```

For troubleshooting, log:

```text
HTTP status code
response headers
response body
```

Avoid logging credentials or sensitive authentication data.

### No SMS is being sent

Check the following:

1. `dry_run` is disabled.
2. Problems are actually being returned by Dynatrace.
3. Recipients are configured for the applicable escalation level.
4. The problem severity matches the configured severity.
5. The SMS API URL is reachable from the ActiveGate.
6. The SMS API credentials are valid.
7. The request matches the SMS gateway's expected format.
8. The extension logs do not contain `SmsClientError`.

### Problems are not being processed

Check:

```text
lookback_window
```

and:

```text
max_problems_per_execution
```

Also verify that the Management Zone configuration is correct.

If Management Zones are intentionally empty, confirm that the problem query interprets the empty list as **all Management Zones**.

### Escalation is not occurring

Verify:

```text
L2 escalation delay
L3 escalation delay
```

and ensure:

```text
L2 delay < L3 delay
```

Also verify that the problem remains open long enough to reach the configured escalation thresholds.

The cache stores the current escalation level, so inspect the cache state when investigating escalation behavior.

### Cache problems

The plugin uses two cache files:

```text
problem_cache.json
synthetic_problem_cache.json
```

The first stores standard problems and the second stores synthetic problems.

to retain problem state between executions.

The cache contains information such as:

- Problem ID.
- Problem status.
- Problem start time.
- Current escalation level.
- Last notification type.
- Last update time.

If troubleshooting cache behavior, first determine the actual working/cache directory used by the extension runtime rather than assuming it is located in the project directory.

Also be careful when running multiple extension instances/configurations on the same host: cache-file isolation should be verified for the specific Dynatrace runtime deployment.

### Certificate / connectivity issues

If the SMS API or Dynatrace endpoint uses TLS certificates, verify:

- Certificate chain.
- CA certificate availability.
- File permissions.
- Runtime user permissions.
- ActiveGate connectivity.
- Proxy configuration.

The certificate must be readable by the user under which the relevant Dynatrace component is running.

### Check extension logs

The most useful information when troubleshooting is the extension task log.

Look for:

```text
Initializing DT SMS Plugin...
Initialization completed.
Query started.
Failed to send SMS:
Initialization failed
SmsClientError
```

Also check the surrounding Dynatrace ActiveGate/remote-plugin runtime logs for Python environment and extension lifecycle errors.
