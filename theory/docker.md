# Разбор docker-compose (построчно)

## Исходный фрагмент

```yaml
services:
  postgres:
    image: postgres:17
    container_name: speechmate-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_HOST_AUTH_METHOD: trust
    ports:
      - "${DB_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5
```

## Пояснение каждой строки

1. `services:`  
   Корневой раздел Docker Compose. В нем перечисляются все сервисы (контейнеры) проекта.

2. `postgres:`  
   Имя сервиса. По этому имени к БД могут обращаться другие сервисы внутри сети Compose.

3. `image: postgres:17`  
   Используется официальный образ PostgreSQL версии `17`.

4. `container_name: speechmate-postgres`  
   Явно задается имя контейнера в Docker, чтобы не использовать автосгенерированное.

5. `restart: unless-stopped`  
   Политика перезапуска: контейнер перезапускается автоматически, если упал или после рестарта Docker, пока не остановлен вручную.

6. `environment:`  
   Блок переменных окружения, передаваемых в контейнер.

7. `POSTGRES_USER: ${DB_USER}`  
   Логин пользователя PostgreSQL берется из переменной окружения `DB_USER`.

8. `POSTGRES_PASSWORD: ${DB_PASSWORD}`  
   Пароль пользователя PostgreSQL берется из переменной `DB_PASSWORD`.

9. `POSTGRES_DB: ${DB_NAME}`  
   Имя базы данных, создаваемой при первом запуске, берется из `DB_NAME`.

10. `POSTGRES_HOST_AUTH_METHOD: trust`  
    Упрощенная схема аутентификации (`trust`), позволяющая подключения без проверки пароля в ряде случаев. Подходит только для локальной разработки, небезопасно для продакшена.

11. `ports:`  
    Раздел проброса портов контейнера на хост.

12. `- "${DB_PORT}:5432"`  
    Порт `5432` внутри контейнера (Postgres) пробрасывается на порт хоста, указанный в `DB_PORT`.

13. `volumes:`  
    Раздел подключения томов для постоянного хранения данных.

14. `- postgres_data:/var/lib/postgresql/data`  
    Именованный том `postgres_data` монтируется в директорию данных PostgreSQL, чтобы данные не терялись при пересоздании контейнера.

15. `healthcheck:`  
    Раздел проверки здоровья контейнера.

16. `test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]`  
    Команда проверки: `pg_isready` проверяет, готов ли Postgres принимать подключения от пользователя `${DB_USER}`.

17. `interval: 5s`  
    Проверка выполняется каждые 5 секунд.

18. `timeout: 5s`  
    Максимальное время ожидания ответа одной проверки — 5 секунд.

19. `retries: 5`  
    После 5 подряд неудачных проверок контейнер помечается как `unhealthy`.