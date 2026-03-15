# KubeTix Helm Chart

Helm chart for deploying KubeTix - Temporary Kubernetes Access Manager.

## Prerequisites

- Kubernetes 1.25+
- Helm 3+
- Ingress controller (nginx recommended)
- cert-manager (optional, for TLS)

## Install

```bash
# Add repository
helm repo add kubetix https://joryirving.github.io/kubetix-helm
helm repo update

# Install with defaults
helm install kubetix kubetix/kubetix \
  --namespace kubetix \
  --create-namespace

# Install with custom values
helm install kubetix kubetix/kubetix \
  --namespace kubetix \
  --create-namespace \
  --set ingress.hosts[0].host=kubetix.example.com \
  --set database.postgresql.auth.password=<secure-password>
```

## Uninstall

```bash
helm uninstall kubetix --namespace kubetix
```

## Configuration

The following table lists the configurable parameters of the KubeTix chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | API image repository | `ghcr.io/joryirving/kubetix-api` |
| `image.tag` | API image tag | `Chart.AppVersion` |
| `replicaCount` | Number of API replicas | `1` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8000` |
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts[0].host` | Ingress host | `kubetix.example.com` |
| `ingress.tls` | TLS configuration | `kubetix-tls` |
| `resources` | Resource limits | See values.yaml |
| `autoscaling.enabled` | Enable HPA | `false` |
| `autoscaling.minReplicas` | Minimum replicas | `1` |
| `autoscaling.maxReplicas` | Maximum replicas | `5` |
| `database.external.enabled` | Use external DB | `false` |
| `database.postgresql.enabled` | Use Bitnami PostgreSQL | `true` |
| `database.postgresql.persistence.size` | DB storage size | `10Gi` |
| `oidc.enabled` | Enable OIDC | `false` |
| `oidc.issuer` | OIDC issuer URL | `""` |
| `oidc.clientId` | OIDC client ID | `""` |
| `oidc.clientSecret` | OIDC client secret | `""` |

### Database Configuration

#### External Database

```bash
helm install kubetix kubetix/kubetix \
  --set database.external.enabled=true \
  --set database.external.host=external-db.example.com \
  --set database.external.username=kubetix \
  --set database.external.password=secret \
  --set database.external.database=kubetix
```

#### Bitnami PostgreSQL (Default)

```bash
helm install kubetix kubetix/kubetix \
  --set database.postgresql.auth.password=<secure-password> \
  --set database.postgresql.persistence.size=20Gi
```

### OIDC Configuration

Enable OIDC authentication (e.g., Authentik, Keycloak, Okta):

```bash
helm install kubetix kubetix/kubetix \
  --set oidc.enabled=true \
  --set oidc.issuer=https://authentik.example.com \
  --set oidc.clientId=kubetix \
  --set oidc.clientSecret=<your-secret> \
  --set oidc.redirectUri=https://kubetix.example.com/auth/oidc/callback
```

### Autoscaling

Enable horizontal pod autoscaling:

```bash
helm install kubetix kubetix/kubetix \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=2 \
  --set autoscaling.maxReplicas=10 \
  --set autoscaling.targetCPUUtilizationPercentage=70
```

## Values File

See `values.yaml` for complete configuration options.

## Troubleshooting

```bash
# Check deployment status
helm status kubetix --namespace kubetix

# View logs
kubectl logs -l app.kubernetes.io/name=kubetix --namespace kubetix

# Check events
kubectl get events --namespace kubetix --sort-by='.lastTimestamp'

# Debug database
kubectl port-forward svc/{{ .Release.Name }}-postgresql 5432:5432 --namespace kubetix
```

## License

MIT License
