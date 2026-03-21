# damex.cloudflare

[![](https://github.com/damex/ansible-collections-cloudflare/workflows/linting/badge.svg)](https://github.com/damex/ansible-collections-cloudflare/actions)

Ansible collection for [Cloudflare](https://www.cloudflare.com/).

## Modules

| Module | Description |
|--------|-------------|
| `cloudflare_zone` | Ensure Cloudflare zone |

## Roles

| Role | Description |
|------|-------------|
| `cloudflare_acme` | Ensure Cloudflare ACME |
| `cloudflare_dns` | Ensure Cloudflare DNS |
| `cloudflare_zones` | Ensure Cloudflare zones |

## Requirements

- Ansible core >= 2.19.0
- python3-cloudflare >= 2.11.1
- Debian or Fedora or Red Hat Enterprise Linux derivatives

## Installation

```
ansible-galaxy collection install damex.cloudflare
```

Or via `requirements.yml`:

```yaml
collections:
  - name: damex.cloudflare
    version: 1.0.6
```

```
ansible-galaxy collection install -r requirements.yml
```

## Issues

Bug reports and feature requests are welcome at [GitHub Issues](https://github.com/damex/ansible-collections-cloudflare/issues).
