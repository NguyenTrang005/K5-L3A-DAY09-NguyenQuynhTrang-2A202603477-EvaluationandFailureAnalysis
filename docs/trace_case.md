# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-014 --seed 11
python -m lab9.trace_case --shape fixed --claim C-014 --seed 11   
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case phân tích: C-014 — trừ lịch sử hoàn hai lần

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-014@11`; run ID: `R-seeded_regression-C-014-s11`. |
| Triệu chứng | Grader Lab 8 báo `FAIL (proposal_mismatch)`. Ledger ghi khoản hoàn mới 90.000đ, trong khi nhãn yêu cầu 120.000đ. Reply thông báo đã hoàn 120.000đ. |
| Bước sai đầu tiên | Event 5, kind `proposal`, payload `{"amount_vnd": 120000}`: agent đã trừ 30.000đ lịch sử hoàn khỏi quote trước khi gửi host. |
| Vì sao là bước *đầu tiên* | Event 1–2 chưa cho thấy sai lệch trong handoff và tra đơn. Event 3 tính quote đúng là 150.000đ; event 4 đọc lịch sử đã hoàn 30.000đ. Sai lệch bắt đầu khi event 5 giảm proposal xuống 120.000đ; host tiếp tục trừ lịch sử 30.000đ nên chỉ hoàn mới 90.000đ. |
| Failure mode | Lỗi chính FM-05 — `pre_deducted`. Ngoài ra, event 6 có FM-08 — `misreport`: reply báo hoàn 120.000đ nhưng ledger chỉ ghi 90.000đ. |
| Đối chứng | `fixed C-014@11` giữ quote đầy đủ 150.000đ cho host xử lý. Ledger ghi khoản hoàn mới 120.000đ, reply khớp ledger, status `resolved`; grader Lab 8 báo `PASS (ok)`. |
| Regression test | `src/tests/test_lab9_trace_case.py`: `test_lab9_c014_fixed_preserves_full_quote` xác nhận quote 150.000đ, ledger 120.000đ và grader PASS. `test_lab9_c014_detects_double_deduction` xác nhận bản lỗi có proposal 120.000đ, ledger 90.000đ, event 5 là proposal sai và grader FAIL; dùng `pytest.raises` để chứng minh cùng kiểm tra hợp đồng từ chối bản lỗi. Chạy từ `src`: `python -m pytest -q -o addopts= tests/test_lab9_trace_case.py` → **2 passed**. |
| Chưa chắc chắn | Trace không hiển thị một event riêng cho phép trừ bên trong host; cơ chế trừ lần hai cần đối chiếu code host. Case này chỉ kiểm tra C-014 ở seed 11, chưa chứng minh kết quả trên mọi claim và seed. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
