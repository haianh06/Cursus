import React from 'react';
import { useLanguage } from '../../context/LanguageContext';
import LegalPageLayout from './LegalPageLayout';

/**
 * Draft Terms of Service — a standard-shape starting point covering the
 * facts already true in this codebase (institution-issued accounts, no
 * public self-signup, the sandbox trial, the academic-integrity guardrail
 * behavior). NOT reviewed by counsel — the product owner should have this
 * checked before relying on it, especially the liability/warranty sections.
 */
export default function TermsOfServiceScreen() {
  const { lang } = useLanguage();
  const vi = lang === 'vi';

  return (
    <LegalPageLayout
      title={vi ? 'Điều khoản Dịch vụ' : 'Terms of Service'}
      updatedAtLabel={vi ? 'Có hiệu lực từ: 18/08/2026' : 'Effective: August 18, 2026'}
    >
      <section>
        <h2>{vi ? '1. Chấp nhận điều khoản' : '1. Acceptance of Terms'}</h2>
        <p>
          {vi
            ? 'Bằng việc truy cập hoặc sử dụng Cursus (bao gồm tài khoản thật do tổ chức cấp và trải nghiệm sandbox không cần tài khoản), bạn đồng ý với các điều khoản dưới đây.'
            : 'By accessing or using Cursus (including institution-issued real accounts and the no-account sandbox trial), you agree to the terms below.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '2. Tài khoản và quyền truy cập' : '2. Accounts & Access'}</h2>
        <p>
          {vi
            ? 'Cursus không có đăng ký công khai. Tài khoản thật được cấp bởi tổ chức giáo dục của bạn (sinh viên được nhập/mời, giảng viên được quản trị viên mời, quản trị viên được cấp khi khởi tạo tổ chức). Bạn chịu trách nhiệm bảo mật thông tin đăng nhập của mình.'
            : 'Cursus has no public sign-up. Real accounts are issued by your educational institution (students are imported/invited, teachers are invited by an admin, admins are provisioned when the organization is set up). You are responsible for keeping your login credentials secure.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '3. Trải nghiệm sandbox' : '3. Sandbox Trial'}</h2>
        <p>
          {vi
            ? 'Trải nghiệm sandbox 3 vai trò sử dụng dữ liệu minh họa trong một tổ chức mẫu, tách biệt hoàn toàn khỏi dữ liệu thật. Trải nghiệm này chỉ nhằm mục đích giới thiệu sản phẩm và có thể bị giới hạn hoặc thay đổi bất kỳ lúc nào mà không cần báo trước.'
            : 'The 3-role sandbox trial uses sample data inside a demonstration organization, fully isolated from real data. It exists solely to showcase the product and may be limited or changed at any time without notice.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '4. Sử dụng đúng mục đích và Liêm chính học thuật' : '4. Acceptable Use & Academic Integrity'}</h2>
        <p>
          {vi
            ? 'Trợ lý Cursus được thiết kế để hỗ trợ học tập, không thay thế việc tự học. Bạn đồng ý không cố gắng vượt qua các cơ chế bảo vệ liêm chính học thuật của Trợ lý Cursus (ví dụ: yêu cầu Trợ lý Cursus viết bài/code hộ). Chúng tôi có quyền tạm ngưng tài khoản vi phạm nghiêm trọng và lặp lại các điều khoản này.'
            : 'Cursus Assistant is designed to support learning, not to replace it. You agree not to attempt to circumvent Cursus Assistant\'s academic-integrity safeguards (e.g. asking Cursus Assistant to write assignments or code on your behalf). We reserve the right to suspend accounts for serious or repeated violations of these terms.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '5. Nội dung do AI tạo ra' : '5. AI-Generated Content'}</h2>
        <p>
          {vi
            ? 'Câu trả lời của Trợ lý Cursus được tạo bởi AI và có thể chứa sai sót, kể cả khi có trích dẫn nguồn. Bạn nên tự kiểm chứng thông tin quan trọng, đặc biệt liên quan đến quy định của môn học hoặc điều kiện tốt nghiệp.'
            : 'Cursus Assistant\'s responses are AI-generated and may contain errors, even when citations are shown. You should independently verify anything important, especially course policy details or graduation requirements.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '6. Sở hữu trí tuệ' : '6. Intellectual Property'}</h2>
        <p>
          {vi
            ? 'Cursus và các thương hiệu, giao diện, mã nguồn liên quan thuộc quyền sở hữu của Cursus. Học liệu bạn tải lên vẫn thuộc quyền sở hữu của bạn hoặc tổ chức của bạn; chúng tôi chỉ sử dụng học liệu đó để cung cấp dịch vụ cho bạn.'
            : 'Cursus and its associated branding, interface, and source code are owned by Cursus. Course materials you upload remain the property of you or your institution; we use them only to provide the service to you.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '7. Giới hạn trách nhiệm' : '7. Limitation of Liability'}</h2>
        <p>
          {vi
            ? 'Cursus được cung cấp "nguyên trạng". Trong phạm vi pháp luật cho phép, chúng tôi không chịu trách nhiệm cho các quyết định học tập được đưa ra dựa trên gợi ý của Trợ lý Cursus mà không được người dùng tự kiểm chứng.'
            : 'Cursus is provided "as is". To the extent permitted by law, we are not liable for academic decisions made based on Cursus Assistant\'s suggestions without independent verification by the user.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '8. Chấm dứt' : '8. Termination'}</h2>
        <p>
          {vi
            ? 'Quyền truy cập tài khoản thật gắn với thời hạn hợp đồng giữa Cursus và tổ chức của bạn, và có thể bị chấm dứt khi hợp đồng đó kết thúc hoặc khi tổ chức yêu cầu.'
            : 'Access to real accounts is tied to the contract term between Cursus and your institution, and may be terminated when that contract ends or at your institution\'s request.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '9. Thay đổi điều khoản' : '9. Changes to These Terms'}</h2>
        <p>
          {vi
            ? 'Chúng tôi có thể cập nhật các điều khoản này theo thời gian. Ngày hiệu lực ở đầu trang sẽ được cập nhật khi có thay đổi đáng kể.'
            : 'We may update these terms from time to time. The effective date at the top of this page will be updated when material changes are made.'}
        </p>
      </section>

      <section>
        <h2>{vi ? '10. Liên hệ' : '10. Contact'}</h2>
        <p>
          {vi ? 'Mọi câu hỏi về điều khoản dịch vụ, vui lòng liên hệ: ' : 'For any questions about these terms, please contact: '}
          <a href="mailto:support@cursus.edu.vn">support@cursus.edu.vn</a>
        </p>
      </section>
    </LegalPageLayout>
  );
}
