<!-- Modified by china-market-data contributors: extracted and updated from a-stock-data; see ../UPSTREAM.md and ../NOTICE. -->

# ETF 期权合约与指标

查询合约清单、单合约报价或希腊字母时读取 [§9.1](#options)。`<skill目录>` 为技能根目录；Python 组合调用先执行 [路径初始化](../SKILL.md#python-脚本路径初始化)。其他章节见 [SKILL.md](../SKILL.md)。

> 50ETF / 300ETF / 科创50ETF / 500ETF 期权（#13）。走新浪源——**T型报价、希腊字母、隐含波动率均由交易所/新浪预先算好，无需本地算 BSM**。免费直连，唯一注意带 `Referer`。

<a id="options"></a>

### 9.1 合约清单 + T型报价 + 希腊字母

实现位于 [scripts/sina_options.py](../scripts/sina_options.py)，依赖 requests：

```bash
python3 "<skill目录>/scripts/sina_options.py" codes --underlying 510050 --output calls.json
python3 "<skill目录>/scripts/sina_options.py" codes --underlying 510050 --put --output puts.json
python3 "<skill目录>/scripts/sina_options.py" quote <合约代码> --output quote.json
python3 "<skill目录>/scripts/sina_options.py" greeks <合约代码> --output greeks.json
```

codes 默认认购，--put 认沽；月份列表先去掉首项，再去横线、截后四位，保持源顺序，只保留非空合约月份，不额外排序或去重。支持510050/510300/588000/510500的类别映射；未知 underlying 仍按原行为查询50ETF月份，但合约列表请求保留原underlying，不能视为任意标的都支持。

行情原始GBK逗号数组，报价少于43项或greeks少于16项返回{}。数值字段尝试float，失败保留原值，空串/横线不强制置零；名称与交易代码保持字符串。greeks必须跳过raw[1:4]，IV仍为小数，不乘100，也不本地计算BSM。

CLI保存完整字典，codes终端仅预览前三个月、每月前三个代码并报告总月份/合约数；quote/greeks完整预览。NaN/Infinity用显式$float标记保存。月份请求失败原生函数WARN+{}，CLI对此非零退出且不保存；无WARN的短报价/空月份仍保持空对象，不能据此认定数据源有效。后续逐月请求和解析异常原样失败。已有输出含符号链接不覆盖。

Python组合调用先初始化脚本路径；下例仅查询源列表首个非空月份的首个认购合约，**不代表近月或平值，也不是认购认沽配对的完整 T 型链**。指定期限、平值或配对任务须另核验到期日、标的行情、行权价和合约规格，不能按列表位置推断：

```python
import io
import math
from contextlib import redirect_stdout
from sina_options import sina_option_codes, sina_option_tquote, sina_option_greeks

# 仅演示查询一个返回合约，不按源顺序认定近月或平值。
diagnostics = io.StringIO()
with redirect_stdout(diagnostics):
    codes = sina_option_codes("510050", call=True)
if "[WARN]" in diagnostics.getvalue():
    raise RuntimeError("合约列表请求失败：" + diagnostics.getvalue())
selected = next(((month, contracts[0]) for month, contracts in codes.items() if contracts), None)
if selected is None:
    print("未取得合约列表，不能据此认定没有可交易合约。")
else:
    month, code = selected
    q, g = sina_option_tquote(code), sina_option_greeks(code)
    print(f"返回月份标签 {month}，示例认购合约 {code}（未核验到期排序或平值）")
    print("报价原始字段:", q if q else "未取得报价")
    print("希腊字母原始字段:", g if g else "未取得希腊字母")
    iv = g.get("iv")
    if isinstance(iv, (int, float)) and not isinstance(iv, bool) and math.isfinite(iv) and iv >= 0:
        print(f"源 IV: {iv:.2%}")
    else:
        print("IV 未取得有效数值，不补零。")
```

> **坑：** ① 新浪源 **GBK 编码**、**逗号分隔**、需去 `var hq_str_XXX="..."` 壳。② 必带 `Referer: https://stock.finance.sina.com.cn/`，否则 403。③ 希腊字母解析 **`[raw[0]] + raw[4:]`**——`raw[1:4]` 是 3 个空串，不跳过则 Delta/IV 全错位。④ `iv` 是小数（0.1735 = 17.35%）。⑤ 300ETF(510300)、科创50ETF(588000) 同理，换 `underlying` 即可。

---
