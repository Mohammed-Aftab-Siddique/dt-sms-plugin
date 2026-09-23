# Dynatrace SMS Notification Plugin

## Overview

The **Dynatrace SMS Notification Plugin** is a custom Dynatrace Python extension that monitors Dynatrace problems and sends SMS notifications based on configurable severity and escalation rules.

### Common Capabilities

The following capabilities are shared by both documented versions:

- Polls Dynatrace for active and recently closed problems.
- Filters problems by one required Management Zone configured during activation.
- Sends SMS notifications for newly detected problems.
- Supports **L1, L2, and L3 escalation levels**.
- Escalates notifications based on configurable time thresholds.
- Sends cumulative notifications when a problem is closed.
- Maintains local problem state to track notifications and escalation levels.
- Supports **dry-run mode** for testing without sending SMS.
- Publishes custom metrics for processing time, processed problems, SMS activity, and execution health.
- Sends form-encoded requests to the configured SMS gateway.

---

## Capabilities by Version

### v1.1.1 — Standard Problem Notifications

Version 1.1.1 contains the original extension behavior:

- Processes problems through a single standard-notification pipeline.
- Selects the initial L1, L2, or L3 level from the Dynatrace problem severity.
- Escalates existing open problems according to the configured L2 and L3 delays.
- Sends cumulative closure notifications to every recipient level reached by the problem.
- Uses `problem_cache.json` for problem and escalation state.
- Uses the standard SMS payload containing Application, Incident, Severity, Status, Entity, Time, and `DT`.
- Does not distinguish synthetic problems from other Dynatrace problems or provide synthetic-specific settings.

### v2.0.0 — Synthetic Problem Support

Version 2.0.0 preserves the standard-notification flow and adds:

- Optional synthetic handling, disabled by default.
- Detection of `SYNTHETIC_TEST` and `HTTP_CHECK` affected-entity types.
- Complete exclusion of synthetic problems when synthetic handling is disabled.
- A dedicated synthetic payload using:
  - The configured Management Zone from the activation settings as Application.
  - `dt.synthetic.step.name` from problem evidence as Incident.
  - The matching affected-entity name as Flow Name.
- Delay-only synthetic escalation that always begins at L1 and does not use severity.
- An option to reuse standard recipients and delays for synthetic escalation.
- Dedicated synthetic L1/L2/L3 recipients and L2/L3 delays when shared settings are disabled.
- Separate `problem_cache.json` and `synthetic_problem_cache.json` state files.
- Escalation levels in all open statuses, such as `OPEN L1`, `OPEN L2`, and `OPEN L3`.
- Closed statuses without an escalation suffix.
- Conditional activation-schema fields and defaults for every non-nullable setting.
- Retrieval and parsing of Dynatrace `evidenceDetails` for synthetic step names.

### v2.0.1 — Selective Synthetic Evidence Retrieval

Version 2.0.1 keeps the main Problems API query at `pageSize=100` without expanded fields. When synthetic
handling is enabled, the extension retrieves `evidenceDetails` individually only for identified synthetic
problems. This avoids the smaller page-size constraint applied by Dynatrace when expanded fields are requested
on the problem-list endpoint. When synthetic handling is disabled, no evidence-detail requests are made.

### v2.0.2 — Required Single Management Zone

Version 2.0.2 replaces the optional Management Zone list with one required Management Zone activation field.
That value filters the Problems API query and supplies the `Application` line in both standard and synthetic
SMS payloads. Management-zone values returned in problem payloads are not used.

---

## Architecture (v2.0.0)

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
version: 2.0.2
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

#### Management Zone

Specify the single Management Zone to monitor. This field is required. The value is used both to filter the
Dynatrace Problems API query and as the `Application` value in standard and synthetic SMS payloads.

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

Both payload types use the Management Zone configured in the activation settings as the application name.
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

The Management Zone activation field is required. Enter the exact zone name used in Dynatrace. The plugin
uses it for Problems API filtering and for the `Application` line in both SMS payload formats.

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

Confirm that the configured Management Zone exactly matches the zone name in Dynatrace.

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
