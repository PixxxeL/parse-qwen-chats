# Парсер чатов Qwen

Не судите строго - набросок "на ходу"

## Running

Для запуска понадобятся переменные окружения

* `QWEN_USER` - логин
* `QWEN_PASSWORD` - пароль
* `FIREFOX_BINARY` - где исполняемый файл Firefox
* `GECKO_BINARY` - где исполняемый файл Gecko Driver

И потребуется установить пакет Selenium.

Запускал на Python 3.12, но думаю до 3.8 вниз будет работать, хоть и не факт.

## To Do

1. Проектные чаты зря так сложно - есть в списке кнопки
2. Заменить бы где возможно WebDriverWait
3. Не грузятся чаты проектов по кнопке "Больше проектов"
4. Не собираются из папок, только проекты (не все, п. 3) и чаты

## Структура сайдбара

```
#sidebar
    .sidebar-side.side-mobile-width
        ...
        .sidebar-new-list-content
            ...
            .project-list-wrapper
                ...
                .project-container
                    ...
                    .project-list
                        .project-item // New Project
                        ...
                        .project-item // Show more
            .session-list-wrapper
                .session-list
                    .recursive-folder-dragge.folder-list []
                    .list-folder
                        .collapsible-full
        ...
```

