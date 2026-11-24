# Android Auto для Geely — форк OXIDIZ

Сборка Open Headunit для Geely OneOS использует пакет `com.geely.headunitrevived`. Особенности экрана, климата, ввода, навигации, оформления и обновлений описаны в [описании сборки](RELEASE.ru.md).

## Однократная настройка GitHub

1. Откройте **Actions** и включите workflows для форка, если GitHub предлагает кнопку включения.
2. Откройте **Settings → Secrets and variables → Actions → New repository secret**:
   https://github.com/OXIDIZ/open-headunit/settings/secrets/actions/new
3. Имя секрета: **GEELY_SIGNING**. Значение: всё содержимое файла **github-secret.json** из предоставленного отдельно резервного архива ключа. Этот файл содержит ключ и пароли: его не нужно коммитить или добавлять в Issues.
4. В **Actions → Geely APK and stable OHU updates → Run workflow** запустите сборку на main.

Если GitHub запрещает workflow запись содержимого, проверьте **Settings → Actions → General → Workflow permissions**. Workflow объявляет contents: write; ограничения организации могут потребовать изменения администратором.

После успешной проверки подписанный APK появится в **Releases**:
https://github.com/OXIDIZ/open-headunit/releases

Без GEELY_SIGNING код и сборочные проверки выполняются, но создаётся только **неподписанный** artifact; такой APK не публикуется как готовый установочный релиз. Случайный временный ключ GitHub runner не используется для release.

## Автоматические обновления OHU

Workflow ежедневно проверяет последний **стабильный** GitHub Release andreknieriem/open-headunit, примерно в **07:17 по Москве** (04:17 UTC; расписание GitHub может задерживаться).

1. Получает точный tag релиза и фиксирует его commit SHA в geely/upstream.json.
2. Если релиз уже является предком main, не откатывает более новую базу форка.
3. Вливает новый upstream в локальную копию, сохраняя собственные коммиты форка.
4. Устанавливает версии Android SDK/NDK/CMake из обновлённого app/build.gradle.kts, выполняет unit-тесты, connection lifecycle harness, собирает APK и проверяет пакет, название, локали, фильтр ECARX, permissions, ABI и подпись.
5. Только после успешных проверок отправляет обычный merge в main и публикует подписанный APK.

При конфликте merge отменяется и workflow завершается ошибкой. При ошибке тестов или проверки APK обновление не отправляется в main и не публикуется. Force push не используется. Если во время сборки пользователь изменил main, обычный push отклонится, сохранив его изменения.

Текущая стартовая база форка — main оригинального проекта, commit 574ce83f6a36c874e7f8aaabe30c10cc90f6289e. Она уже содержит изменения после stable 4.0.0. Состояние geely/upstream.json обозначает последний учтённый стабильный релиз, а не утверждает, что в исходниках нет более поздних коммитов.

Если tag этого коммита уже существует, workflow сохраняет опубликованный APK. Каждый новый коммит форка получает отдельный tag, а номер версии установленного приложения остаётся равным OHU. Если долго не пользоваться форком, GitHub может приостановить scheduled workflows; их можно снова включить в Actions.

## Локальная сборка

Нужны JDK 21, Android SDK 36, build-tools 36.0.0, NDK 29.0.14206865 и CMake 3.22.1.

```sh
python3 -m unittest discover -s tools/geely -p 'test_*.py' -v
./gradlew :app:testGithubDebugUnitTest :app:assembleGithubRelease
python3 -u app/src/test/host-connection/run.py
python3 tools/geely/verify_apk.py app/build/outputs/apk/github/release/*.apk --require-signature
```

Для подписи положите локальный key.properties в корень проекта (он игнорируется Git), указав storeFile, storePassword, keyAlias и keyPassword. Значение storeFile разрешается относительно app/. Для абсолютного пути используйте полный путь к вашему keystore.

После настройки одного GEELY_SIGNING тот же конфиг можно применить локально через tools/geely/configure_signing.py. Не передавайте секреты непосредственно в командной строке или в публичных логах.

Полная совместимость с конкретной прошивкой Geely требует проверки на головном устройстве: CI проверяет код и APK, но не физическое климатическое оборудование автомобиля.
