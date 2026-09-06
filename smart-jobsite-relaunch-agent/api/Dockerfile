# api/Dockerfile — image de l'API FastAPI minimale du Jour 4 (avancée
# depuis le Jour 5 pour débloquer le workflow n8n, cf. résumé de reprise).
#
# Construit depuis la RACINE du repo (docker-compose.yml définit
# context: .) car l'API importe le package agent/ qui est un frère de api/.

FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY agent/ agent/
COPY api/ api/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
