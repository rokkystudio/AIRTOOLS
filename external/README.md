# External Sources

Каталог `external` используется для сторонних исходников и архивов, необходимых для исследования драйверов и firmware.

В Git сохраняется архив:

```text
external\linux-2.6.36.tar.xz
```

SHA256:

```text
8FEFFB29AD70EADCAC9AE70F19F455A12C58B166F82E5CAC4B62FFF57FC0A9F0
```

Распакованные kernel/vendor trees и временные архивы в Git не хранятся. Рабочие деревья можно распаковывать непосредственно в `external`; `.gitignore` исключает их из репозитория.