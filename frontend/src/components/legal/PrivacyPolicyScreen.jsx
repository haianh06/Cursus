import React from 'react';
import { useLanguage } from '../../context/LanguageContext';
import LegalPageLayout from './LegalPageLayout';

/**
 * Draft Privacy Policy — a reasonable, standard-shape starting point for an
 * EdTech product, written from what's actually true in this codebase (the
 * student/instructor data-separation model, sandbox isolation, Google
 * OAuth, support@cursus.edu.vn). This has NOT been reviewed by counsel —
 * treat every claim here as something the product owner must verify before
 * launch, especially around data retention periods and any jurisdiction-
 * specific obligations (FERPA, GDPR, Vietnam's Decree 13/2023, etc.).
 */
export default function PrivacyPolicyScreen() {
  const { lang } = useLanguage();
  const vi = lang === 'vi';

  return (
    <LegalPageLayout
      title={vi ? 'Chính sách Bảo mật' : 'Privacy Policy'}
      updatedAtLabel={vi ? 'Có hiệu lực từ: 18/08/2026' : 'Effective: August 18, 2026'}
    >
      <section>
        <h2>{vi ? '1. Giới thiệu' : '1. Introduction'}</h2>
        <p>
          {vi
            ? 'Chính sách này giải thích cách Cursus ("chúng tôi") thu thập, sử dụng và bảo vệ thông tin khi bạn sử dụng nền tảng Cursus — bao gồm website, ứng dụng, và trải nghiệm sandbox không cần tài khoản. Tài khoản Cursus được cấp bởi tổ chức giáo dục của bạn (trường/khoa); chính sách này áp dụng cho cả tài khoản thật và trải nghiệm sandbox.'
            : 'This policy explains how Cursus ("we") collects, uses, and protects information when you use the Cursus platform — including the website, the app, and the no-account sandbox trial. Cursus accounts are issued by your educational institution; this policy applies to both real accounts and the sandbox trial.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '2. Thông tin chúng tôi thu thập' : '2. Information We Collect'}</h2>
        <ul>
          <li>
            {vi
              ? <><strong>Thông tin tài khoản:</strong> tên, email trường, vai trò (sinh viên/giảng viên/quản trị viên) — do tổ chức của bạn cung cấp khi cấp tài khoản, hoặc qua đăng nhập Google.</>
              : <><strong>Account information:</strong> name, institutional email, role (student/instructor/admin) — provided by your institution when your account is issued, or via Google sign-in.</>}
          </li>
          <li>
            {vi
              ? <><strong>Học liệu:</strong> syllabus, deadline và tài liệu môn học được tải lên hoặc liên kết để Trợ lý Cursus có thể trích dẫn khi trả lời.</>
              : <><strong>Course materials:</strong> syllabi, deadlines, and course documents uploaded or linked so Cursus Assistant can cite them when answering.</>}
          </li>
          <li>
            {vi
              ? <><strong>Nội dung hội thoại với Trợ lý Cursus:</strong> câu hỏi và câu trả lời trong quá trình bạn tương tác với trợ lý học tập.</>
              : <><strong>Conversations with Cursus Assistant:</strong> the questions and answers exchanged while you use the learning assistant.</>}
          </li>
          <li>
            {vi
              ? <><strong>Dữ liệu sử dụng:</strong> tiến độ kế hoạch tuần, hoạt động check-in, và các thao tác trên nền tảng — dùng để cải thiện sản phẩm và tạo tín hiệu hỗ trợ cho giảng viên.</>
              : <><strong>Usage data:</strong> weekly-plan progress, check-in activity, and in-product actions — used to improve the product and generate support signals for instructors.</>}
          </li>
        </ul>
      </section>

      <section>
        <h2>{vi ? '3. Cách chúng tôi sử dụng thông tin' : '3. How We Use Information'}</h2>
        <p>
          {vi
            ? 'Chúng tôi sử dụng thông tin trên để: tạo kế hoạch học tập cá nhân hoá, trả lời câu hỏi có trích dẫn từ học liệu của bạn, tạo báo cáo tiến độ tổng hợp cho giảng viên, và cải thiện chất lượng sản phẩm. Trợ lý Cursus không sử dụng nội dung hội thoại của bạn để làm bài hộ hoặc tạo ra nội dung vi phạm liêm chính học thuật.'
            : 'We use this information to: generate personalized study plans, answer questions grounded in your course materials, produce aggregated progress reports for instructors, and improve product quality. Cursus Assistant does not use your conversation content to complete assignments on your behalf or to produce content that would violate academic-integrity policy.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '4. Chia sẻ thông tin với giảng viên và tổ chức' : '4. Sharing with Instructors & Institutions'}</h2>
        <p>
          {vi
            ? 'Nội dung hội thoại trực tiếp giữa bạn và Trợ lý Cursus không hiển thị cho giảng viên. Giảng viên và quản trị viên trong tổ chức của bạn chỉ nhận được các chỉ số tổng hợp (ví dụ: tiến độ hoàn thành kế hoạch, cảnh báo nguy cơ trễ hạn) nhằm hỗ trợ bạn kịp thời — không phải nội dung hội thoại nguyên văn.'
            : 'The raw content of your conversations with Cursus Assistant is never shown to instructors. Instructors and admins in your institution only receive aggregated signals (e.g. plan-completion progress, at-risk alerts) to support you in time — never your conversations verbatim.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '5. Dịch vụ bên thứ ba' : '5. Third-Party Services'}</h2>
        <p>
          {vi
            ? 'Cursus có thể sử dụng dịch vụ xác thực (như đăng nhập Google) và hạ tầng AI của bên thứ ba để vận hành trợ lý học tập. Các bên này chỉ xử lý dữ liệu theo phạm vi cần thiết để cung cấp dịch vụ và không được phép sử dụng dữ liệu của bạn cho mục đích khác.'
            : 'Cursus may use third-party authentication (such as Google sign-in) and AI infrastructure providers to operate the learning assistant. These providers process data only to the extent necessary to deliver the service and are not permitted to use your data for other purposes.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '6. Bảo mật dữ liệu' : '6. Data Security'}</h2>
        <p>
          {vi
            ? 'Dữ liệu được truyền tải qua kết nối mã hoá (HTTPS) và quyền truy cập được giới hạn theo vai trò. Trải nghiệm sandbox chạy trên một tổ chức mẫu tách biệt hoàn toàn khỏi dữ liệu thật của bất kỳ trường nào.'
            : 'Data is transmitted over encrypted connections (HTTPS) and access is restricted by role. The sandbox trial runs on a sample organization fully isolated from any institution\'s real data.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '7. Quyền của bạn' : '7. Your Rights'}</h2>
        <p>
          {vi
            ? 'Bạn có thể yêu cầu truy cập, chỉnh sửa hoặc xoá dữ liệu cá nhân của mình bằng cách liên hệ quản trị viên tổ chức của bạn hoặc trực tiếp với chúng tôi qua email bên dưới. Một số yêu cầu có thể cần xử lý qua tổ chức của bạn do dữ liệu thuộc quyền quản lý của tổ chức.'
            : 'You may request access to, correction of, or deletion of your personal data by contacting your institution\'s administrator or us directly at the email below. Some requests may need to go through your institution, since the data is under its administration.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '8. Lưu trữ dữ liệu' : '8. Data Retention'}</h2>
        <p>
          {vi
            ? 'Dữ liệu tài khoản thật được lưu trữ theo thời hạn hợp đồng giữa Cursus và tổ chức của bạn. Dữ liệu phiên sandbox là tạm thời và bị xoá tự động sau một khoảng thời gian ngắn.'
            : 'Real account data is retained per the contract term between Cursus and your institution. Sandbox session data is temporary and automatically deleted after a short period.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '9. Thay đổi chính sách' : '9. Changes to This Policy'}</h2>
        <p>
          {vi
            ? 'Chúng tôi có thể cập nhật chính sách này theo thời gian. Ngày hiệu lực ở đầu trang sẽ được cập nhật khi có thay đổi đáng kể.'
            : 'We may update this policy from time to time. The effective date at the top of this page will be updated when material changes are made.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '10. Liên hệ' : '10. Contact'}</h2>
        <p>
          {vi ? 'Mọi câu hỏi về quyền riêng tư, vui lòng liên hệ: ' : 'For any privacy questions, please contact: '}
          <a href="mailto:support@cursus.edu.vn">support@cursus.edu.vn</a>
        </p>
      </section>
    </LegalPageLayout>
  );
}
