FROM denoland/deno:2.0.0

WORKDIR /app

COPY . .

RUN deno install --allow-scripts
RUN deno task build

EXPOSE 8080

USER deno
CMD ["deno", "task", "start"]


