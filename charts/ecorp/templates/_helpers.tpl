{{/*
Chart name used by the chart label.
*/}}
{{- define "ecorp.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}


{{- define "ecorp.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "ecorp.labels" -}}
app.kubernetes.io/name: {{ include "ecorp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end -}}

{{- define "ecorp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ecorp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "ecorp.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "ecorp.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Name of the Secret holding SECRET_KEY / ADMIN_USERNAME / ADMIN_PASSWORD.
*/}}
{{- define "ecorp.secretName" -}}
{{- default (include "ecorp.fullname" .) .Values.secrets.existingSecret -}}
{{- end -}}
