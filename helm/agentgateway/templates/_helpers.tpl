{{- define "agentgateway.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "agentgateway.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{ include "agentgateway.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "agentgateway.selectorLabels" -}}
app.kubernetes.io/name: agentgateway
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
