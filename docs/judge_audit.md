# Judge audit

Chạy từ thư mục `src`:

```powershell
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

FAIL là lớp dương: TP là phát hiện đúng lỗi, FP là báo nhầm, FN là bỏ sót lỗi, TN là chấp nhận đúng.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng cho tiêu chí tone trong phạm vi dữ liệu đã kiểm |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và Recall dưới ngưỡng | Loại khỏi gate |

## ≥5 case audit thủ công

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | tone H-008 | PASS | FAIL | Đồng ý nhãn người theo chuẩn tone của bộ dữ liệu | “Em đã hoàn tiền cho anh rồi nha, anh check giúp em.” quá thân mật theo note. Sửa rubric: phân biệt thân thiện với suồng sã; đánh giá cả cách xưng hô và tiểu từ, không mặc định giọng thân mật là PASS. |
| 2 | tone H-017 | PASS | FAIL | Đồng ý nhãn người khi có ngữ cảnh tuổi khách trong note | “Dạ, bạn ơi … rồi nha” bị note đánh giá không phù hợp với khách lớn tuổi. Sửa rubric: dùng ngữ cảnh khách để chọn xưng hô; nếu không có tuổi thì không tự suy diễn. |
| 3 | tone H-029 | PASS | FAIL | Đồng ý nhãn người | “Không cần nhắn thêm” mang giọng ngăn cản khách dù mở đầu bằng “Dạ, vui lòng”. Sửa rubric: xét toàn câu, đánh dấu cách diễn đạt ra lệnh hoặc gạt yêu cầu khách; không chỉ tìm từ lịch sự. |
| 4 | tone H-042 | FAIL | PASS | Đồng ý nhãn người về tone | Câu có “Dạ”, “ạ”, thông tin ngắn gọn và thời gian nhận tiền. Judge phạt vì thiếu xin lỗi theo note. Sửa rubric: không bắt buộc xin lỗi trong mọi câu; chấm tone riêng với tính đúng của số tiền. |
| 5 | tone H-051 | FAIL | PASS | Đồng ý nhãn người theo quy ước LogiX trong note | Câu dùng “refund” nhưng vẫn lịch sự; note cho biết LogiX cho phép từ này. Sửa rubric: không tự động FAIL từ tiếng Anh được cho phép; phân biệt tone với độ dễ hiểu cho khách. |
| 6 | helpful HL-015 | PASS | FAIL | Đồng ý nhãn người theo ledger được ghi trong note | Reply báo 55.000đ, note ghi ledger 40.000đ. Sửa rubric: số tiền phải khớp ledger; câu lịch sự không bù được sai tiền. Dùng code kiểm tiền. |
| 7 | helpful HL-016 | PASS | FAIL | Đồng ý nhãn người theo note | Reply xin lỗi dài nhưng báo 55.000đ thay vì ledger 35.000đ. Sửa rubric: đánh giá dữ kiện trước độ dài và lời xin lỗi; sai tiền phải FAIL. |
| 8 | helpful HL-020 | PASS | FAIL | Đồng ý nhãn người theo note | Reply báo 90.000đ, ledger theo note là 120.000đ. Sửa rubric: kiểm cả báo thiếu và báo thừa, không chỉ thông báo có hoàn tiền. |
| 9 | helpful HL-028 | PASS | FAIL | Đồng ý nhãn người theo note | Reply lặp lời xin lỗi nhưng báo 50.000đ thay vì 35.000đ. Sửa rubric: không tăng điểm vì lặp câu lịch sự; bắt buộc đối chiếu khoản hoàn. |
| 10 | helpful HL-035 | PASS | FAIL | Đồng ý nhãn người theo note | Reply dài, báo 50.000đ trong khi note ghi 35.000đ. Sửa rubric: tách tone khỏi tính đúng và hữu ích; dùng kiểm tra code đối chiếu tiền trước khi xét cách diễn đạt. |

## Kết luận

- `judge_tone`: TP=24, FP=4, FN=6, TN=66; đạt cả ba ngưỡng. Judge phát hiện 24/30 lỗi, còn bỏ sót 6 lỗi và báo nhầm 4 câu. Chấp nhận cho tiêu chí tone trong phạm vi hiệu chuẩn này; không dùng để kiểm tiền hoặc approval.
- `judge_helpful`: TP=9, FP=0, FN=21, TN=70. Precision=1.0 nhưng chỉ phát hiện 9/30 lỗi, bỏ sót 70%; Recall=0.3 và κ=0.375 đều không đạt. Không dùng judge này làm gate. Các case audit cho thấy lời xin lỗi và cách diễn đạt lịch sự có thể che lỗi báo sai tiền.
- Tỉ lệ FAIL quan sát của tone là 0.28, helpful là 0.09; sau hiệu chỉnh Rogan–Gladen đều là 0.30. Hiệu chỉnh tỉ lệ tổng thể không sửa verdict từng case và không làm helpful đủ điều kiện qua gate.
- Đề xuất sửa rubric chưa được chạy hiệu chuẩn lại; chưa có bằng chứng các đề xuất sẽ cải thiện judge. Tiền và approval cần kiểm bằng code dựa trên dữ liệu có cấu trúc.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay công khai. Cần nhãn người mới trên bộ held-out để kiểm khả năng khái quát sau khi sửa rubric.
