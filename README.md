# VSTScanningTool

Утилита для сканирования VST2/VST3 плагинов с повышенной точностью:

- нормализация производителей (Sonible, Brainworx/Plugin Alliance, Acustica Audio и др.);
- устранение дубликатов даже при наличии нескольких копий одного и того же плагина;
- чтение метаданных VST3 из `Info.plist` и sidecar JSON для VST2;
- экспорт результата в удобочитаемый `.txt`.

## Использование

```bash
python -m vst_scanning_tool.cli /path/to/VSTPlugins /path/to/VST3 --output plugins.txt
```

Скрипт сформирует `plugins.txt`, сгруппировав плагины по производителям и сохранив тип (VST2/VST3) и версию при наличии.

## Тесты

```bash
python -m unittest
```
