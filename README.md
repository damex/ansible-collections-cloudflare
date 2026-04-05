# damex.cloudflare

[![](https://github.com/damex/ansible-collections-cloudflare/workflows/linting/badge.svg)](https://github.com/damex/ansible-collections-cloudflare/actions)
[![](https://github.com/damex/ansible-collections-cloudflare/workflows/documentation/badge.svg)](https://cloudflare.ansible.damex.org)

Ansible collection for [Cloudflare](https://www.cloudflare.com/).

## Modules

| Module | Description |
|--------|-------------|
| `cloudflare_email_routing` | Ensure Cloudflare email routing |
| `cloudflare_email_routing_address` | Ensure Cloudflare email routing destination address |
| `cloudflare_email_routing_rule` | Ensure Cloudflare email routing rule |
| `cloudflare_dns_record` | Ensure Cloudflare DNS record |
| `cloudflare_dns_record_info` | Ensure Cloudflare DNS record information is gathered |
| `cloudflare_dns_records` | Ensure Cloudflare DNS records for a zone (batch) |
| `cloudflare_pages_project` | Ensure Cloudflare Pages project |
| `cloudflare_r2_bucket` | Ensure Cloudflare R2 bucket |
| `cloudflare_r2_bucket_info` | Ensure Cloudflare R2 bucket information is gathered |
| `cloudflare_tunnel` | Ensure Cloudflare tunnel |
| `cloudflare_tunnel_info` | Ensure Cloudflare tunnel information is gathered |
| `cloudflare_zone` | Ensure Cloudflare zone |

## Roles

| Role | Description |
|------|-------------|
| `cloudflare_acme` | Ensure Cloudflare ACME |
| `cloudflare_dns_records` | Ensure Cloudflare DNS records |
| `cloudflare_email_routing` | Ensure Cloudflare email routing |
| `cloudflare_pages_projects` | Ensure Cloudflare Pages projects |
| `cloudflare_r2_buckets` | Ensure Cloudflare R2 buckets |
| `cloudflare_tunnels` | Ensure Cloudflare tunnels |
| `cloudflare_zones` | Ensure Cloudflare zones |

## Requirements

- Ansible core >= 2.19.0
- Debian or Fedora or Red Hat Enterprise Linux derivatives

## Installation

```
ansible-galaxy collection install damex.cloudflare
```

Or via `requirements.yml`:

```yaml
collections:
  - name: damex.cloudflare
    version: 1.2.2
```

```
ansible-galaxy collection install -r requirements.yml
```

## Migrating from `cloudflare_dns` to `cloudflare_dns_records`

The `cloudflare_dns` role is legacy and requires `community.general` with `python3-cloudflare`.
The `cloudflare_dns_records` role replaces it with no external dependencies and supports 17 record types.

Per-type record lists (`a_records`, `mx_records`, etc.) are replaced by a single `records` list.
Record fields are renamed: `name` becomes `record` (use `@` for zone apex), `value` becomes `content`.

```yaml
# Before (cloudflare_dns)
cloudflare_dns_zones:
  - name: example.com
    a_records:
      - name: www
        value: 192.0.2.1
    mx_records:
      - name: example.com
        value: mail.example.com
        priority: 10

# After (cloudflare_dns_records)
cloudflare_dns_records_zones:
  - name: example.com
    records:
      - record: www
        type: A
        content: 192.0.2.1
      - record: "@"
        type: MX
        content: mail.example.com
        priority: 10
```

## Documentation

Automatically generated documentation is available at [cloudflare.ansible.damex.org](https://cloudflare.ansible.damex.org).

## Issues

Bug reports and feature requests are welcome at [GitHub Issues](https://github.com/damex/ansible-collections-cloudflare/issues).
