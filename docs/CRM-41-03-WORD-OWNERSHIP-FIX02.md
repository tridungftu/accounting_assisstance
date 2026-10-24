# CRM-41-03 · Binding Word local bổ sung FIX02

Ngày 21/10/2026. Quyết định kỹ thuật của Root trong phạm vi CRM G2/G3 đã được giao. Văn bản này thay riêng cách tạo/sở hữu Word và cách bảo vệ native test trong `CRM-41-03-WORD-COM-BINDING.md`; các yêu cầu tài liệu, macro, quyền, CAS, tiền tệ, giữ file và kiểm PDF vẫn giữ. Đây là thay routine provider local đang có, không thêm engine hoặc quy trình nghiệp vụ.

## 1. Tạo tiến trình trước, lấy COM sau

1. Giữ outer Python worker: minimal environment, original no-delete guard A517 và owned Job trước khi nhận stdin/config. Server/module import không kích hoạt COM. Test cha cũng phải gán Job cho native child trước khi mở barrier.
2. Trong worker, kiểm path/hash DOCX và binary Word đã ghim, chụp baseline metadata Word. Dùng `CreateProcessW` với `lpApplicationName` là đúng đường dẫn tuyệt đối WINWORD, command line chỉ binary và **một switch `/w`**, không prepared path/raw path/shell/DDE. Dùng `CREATE_SUSPENDED`, giữ cả process/thread handle do lệnh tạo trả về; gán đúng Word process vào Job, kiểm identity và Job trước `ResumeThread`. Không dùng Popen tạo suspended rồi làm mất thread handle, `NtResumeProcess`, BREAKAWAY, global PID-delta làm bằng chứng hoặc vòng lặp tạo instance.
3. Startup yêu cầu `STARTF_USESHOWWINDOW/SW_HIDE`. Không lấy CREATE_NO_WINDOW làm bằng chứng ẩn ứng dụng GUI. Không ghép `/a`, không sửa registry, Trust Center, Normal.dotm hoặc add-ins. Khả năng ẩn thực tế và tác động tệp tạm native phải báo theo bằng chứng.
4. Chỉ sau Word đã được sở hữu và gán Job mới import/initialize pythoncom/win32com trong worker STA. `pythoncom` có thể initialize khi import; không đưa import ấy lên server/test main. Mọi resource được bảo vệ bởi try/finally từ lúc tạo đầu tiên; cân bằng explicit COM initialization và pointer references.
5. Chờ hữu hạn cửa sổ của **đúng PID/handle vừa tạo**. Chỉ hỏi `_WwG` thuộc PID đó bằng AccessibleObjectFromWindow(OBJID_NATIVEOM, IID_IDispatch), nhận Word.Window rồi Window.Application. Roundtrip Window.Hwnd → GetWindowThreadProcessId phải khớp process handle/PID/start/exe/Job đang giữ. Không bịa Application.Hwnd; không DispatchEx, Caption marker, title search, GetObject/GetActiveObject/ROT fallback hoặc attach PID thay thế.
6. Chỉ sau proof mới đọc/lưu/đặt options, macro ForceDisable, link-update False; mở đúng prepared DOCX theo flags đã chốt. Chỉ giữ Document vừa mở, không enumerate/đọc/đóng tài liệu Word của người dùng.
7. Không có cửa sổ/interface/proof trong hạn: trả NOT_READY/NOT_VERIFIED đúng phase, không Open/COM Quit vào object chưa chứng minh. Dừng bằng chính native handle/Job vừa tạo, chờ terminal và Job-empty; không đụng Word có trước. Không coi thiếu provider là đạt mục tiêu PDF thật.

## 2. Stop và lỗi

- Mọi nhánh spawn/assign/stdin/protocol/EOF/COM/wait/query/timeout/exception phải có cleanup hữu hạn và kết luận worker/Word terminal, Job-empty hoặc UNKNOWN rõ ràng. CloseHandle/KILL_ON_CLOSE đơn lẻ không là stop witness. Nếu chưa gán Job, child chưa được nhận stdin; chỉ dừng exact spawned handle và chờ. Không wildcard kill hoặc suy dừng từ PID scan.
- COM Open/Export/Close/Quit có thể treo. Deadline của outer parent phải dừng đúng owned tree rồi xác minh; không đặt toàn bộ bounded wait sau một synchronous call có thể không trả. Stop chưa xác nhận thì không PDF_DAT/CHO_KY; giữ trạng thái provider chưa sẵn sàng và bằng chứng để đối soát trước lượt tiếp, không tiếp tục mù.
- Giữ gate thành công hiện có: worker exit0, đúng matching Word identity đã Job, Word handle signaled, worker terminal, Job-empty và PDF mới có thật. Giữ immutable DOCX trước PDF và mọi partial PDF/attempt. Không unlink/delete/replace/rename/cleanup. Python guard không chứng minh native Office không tạo/xóa tệp tạm; không ghi báo cáo vượt bằng chứng.

## 3. Native test và nội dung

- `WordThat` dùng native child có Job-before-stdin/deadline/stop proof, không activation/Open/Quit đồng bộ trên test main. Word control tổng hợp của chính test cũng phải được sở hữu/gán Job trước COM/Open và được bảo vệ ngay từ setup/proof. Test treo không được để SCM Word bên ngoài kiểm soát. Baseline Word thật chỉ xem metadata, không đọc tài liệu.
- Availability check chỉ là metadata và không initialize COM trước boundary. Không đổi thiếu provider/ownership thành PASS. Sau review nguồn, Root cần chạy native positive DOCX → Word → PDF, kiểm PDFium/pdfplumber và visual; kiểm control Word/document tổng hợp, baseline user Word và stop thực tế. Fault injection/skip không thay native positive.
- Bộ kiểm văn bản phải cộng số lần yêu cầu của các occurrence có cùng nội dung sau đúng normalization NFC/whitespace hiện hành. Hai field cùng `0`, mỗi field một lần, cần hai occurrence; một `0` phải thiếu. Giữ giá trị một ký tự, Unicode, FX, customer/creator/maintenance và toàn nội dung đã bind. Không đổi typed economics hoặc tự lấy expected từ output. Nhãn vẫn `VAN_BAN_CO_BAN`; bố cục/glyph/vị trí cần kiểm riêng.

## 4. Căn cứ API

- [Office switches: một switch; /w tạo instance mới có blank document](https://support.microsoft.com/en-us/office/lifecycle/command-line-switches-for-microsoft-office-products).
- [CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw), [CREATE_SUSPENDED](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags), [ResumeThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread), [AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject).
- [Word NativeOM](https://learn.microsoft.com/en-us/windows/win32/api/oleacc/nf-oleacc-accessibleobjectfromwindow), [Window.Application](https://learn.microsoft.com/en-us/office/vba/api/word.window.application), [Window.Hwnd](https://learn.microsoft.com/en-us/office/vba/api/word.window.hwnd).

Các API hỗ trợ thiết kế trên; khả năng chạy đúng với Word trên máy Anh chưa được kiểm. Lượt Claude kế tiếp chỉ viết code theo handoff; không tự khởi chạy Word/test/SQL/GUI.
