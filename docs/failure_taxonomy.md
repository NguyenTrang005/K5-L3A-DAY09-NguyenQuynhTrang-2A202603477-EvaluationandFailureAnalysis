# Failure taxonomy v1 (nhóm điền)
| ID | Tên | Định nghĩa (1 câu) | Layer | Bằng chứng (claim@seed / trace) | Grader | Metric |
|---|---|---|---|---|---|---|
| FM-01 | leaky_trace — secret lộ trong trace | | | | | |
| FM-02 | ignore_denied — bỏ qua approval bị từ chối | Agent bỏ qua kết quả từ chối của host và trả trạng thái hoặc thông báo hoàn tiền thành công. | guardrail/approval | seeded_regression C-007@11: event 5 reply báo hoàn 35.000đ, result=resolved nhưng ledger=0đ; fixed trả denied và ledger=0đ. | code | Kiểm tra kết quả denied được phản ánh đúng trong status và reply khi host từ chối approval. |
| FM-03 | ticket_trust — tin ticket hơn DB | Agent dùng thông tin từ ticket để ghi đè dữ liệu đơn hàng có cấu trúc, dẫn đến quyết định hoàn tiền sai. | model/prompt | seeded_regression C-002@11: event 3 model_override đặt delay_days=5, sau đó quote và ledger ghi 20.000đ thay vì 0đ; fixed cùng claim@seed không ghi đè và trả denied. | code | Phát hiện ghi đè dữ liệu order từ ticket; đối chiếu refund_vnd, refund_count và status với nhãn. |
| FM-04 | sum_parts / round_down — cộng/làm tròn sai | Agent cộng các khoản bồi thường hoặc làm tròn trái quy tắc policy, khiến proposal khác quote đúng của tool. | orchestration/state | slice_regression C-014@11: event 3 quote=150.000đ nhưng event 4 proposal=180.000đ; ledger hoàn 150.000đ thay vì 120.000đ; fixed cùng claim@seed đạt PASS. | code | So sánh proposal với quote tính theo policy và khoản hoàn trong ledger với nhãn kỳ vọng. |
| FM-05 | pre_deducted — trừ trước khi được duyệt | Agent trừ khoản hoàn lịch sử khỏi quote trước khi gửi host, khiến host tiếp tục trừ và hoàn thiếu tiền. | orchestration/state | seeded_regression C-014@11: event 3 quote=150.000đ, event 4 history=30.000đ, event 5 proposal=120.000đ; ledger chỉ ghi 90.000đ thay vì 120.000đ. | code | Đối chiếu proposal với quote gốc và khoản hoàn thực tế với entitlement sau khi host xử lý lịch sử. |
| FM-06 | stale_clause — dùng điều khoản cũ | | | | | |
| FM-07 | sibling_refund — hoàn tiền nhầm claim anh em | | | | | |
| FM-08 | misreport — reply nói số tiền khác ledger | Agent thông báo số tiền đã hoàn khác với khoản hoàn thực tế ghi trong ledger. | orchestration/state | seeded_regression C-014@11: event 6 reply báo 120.000đ nhưng ledger=90.000đ; C-007@11 event 5 báo 35.000đ nhưng ledger=0đ. | code | So sánh số tiền được khẳng định đã hoàn trong reply với khoản hoàn thực tế của trial trong ledger. |
| FM-09 | cross_principal — lẫn dữ liệu giữa principal (v2) | | | | | |
Mã và tên ngắn cố định (dùng trong `failure_modes` của eval set); nhóm tự viết định nghĩa, bằng chứng, grader và metric.
Quy tắc: mỗi FM phải quan sát được trên trace, không phải phỏng đoán. Tiền và approval luôn chấm bằng code.
