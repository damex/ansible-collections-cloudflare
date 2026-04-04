# damex.cloudflare

[![](https://github.com/damex/ansible-collections-cloudflare/workflows/linting/badge.svg)](https://github.com/damex/ansible-collections-cloudflare/actions)
[![](https://github.com/damex/ansible-collections-cloudflare/workflows/documentation/badge.svg)](https://cloudflare.ansible.damex.org)

Ansible collection for [Cloudflare](https://www.cloudflare.com/).

## Modules

| Module | Description |
|--------|-------------|
| `cloudflare_r2_bucket` | Ensure Cloudflare R2 bucket |
| `cloudflare_zone` | Ensure Cloudflare zone |

## Roles

| Role | Description |
|------|-------------|
| `cloudflare_acme` | Ensure Cloudflare ACME |
| `cloudflare_dns` | Ensure Cloudflare DNS |
| `cloudflare_r2_buckets` | Ensure Cloudflare R2 buckets |
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
    version: 1.1.0
```

```
ansible-galaxy collection install -r requirements.yml
```

## Documentation

Automatically generated documentation is available at [cloudflare.ansible.damex.org](https://cloudflare.ansible.damex.org).

## Issues

Bug reports and feature requests are welcome at [GitHub Issues](https://github.com/damex/ansible-collections-cloudflare/issues).
