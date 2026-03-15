{{/*
Expand the name of the chart.
*/}}
{{- define "kubetix.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "kubetix.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "kubetix.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "kubetix.labels" -}}
helm.sh/chart: {{ include "kubetix.chart" . }}
{{ include "kubetix.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "kubetix.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kubetix.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "kubetix.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "kubetix.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the database secret
*/}}
{{- define "kubetix.databaseSecretName" -}}
{{- if .Values.database.external.enabled }}
{{- .Values.database.external.existingSecret | default (include "kubetix.fullname" .) }}
{{- else }}
{{- include "kubetix.fullname" . }}
{{- end }}
{{- end }}

{{/*
Create the name of the OIDC secret
*/}}
{{- define "kubetix.oidcSecretName" -}}
{{- if .Values.oidc.enabled }}
{{- printf "%s-oidc" (include "kubetix.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Generate database URL for PostgreSQL
*/}}
{{- define "kubetix.databaseUrl" -}}
{{- $secret := lookup "v1" "Secret" .Release.Namespace .Values.database.postgresql.existingSecret }}
{{- if $secret }}
{{- $key := .Values.database.postgresql.existingSecretPasswordKey | default "database-url" }}
{{- index $secret.data $key | b64dec }}
{{- else }}
{{- fail "Existing secret not found" }}
{{- end }}
{{- end }}
