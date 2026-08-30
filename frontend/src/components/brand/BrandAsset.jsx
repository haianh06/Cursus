import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Cong duy nhat de dua asset thuong hieu (Curi 3D, logo, illustration
 * truong hoc) vao giao dien.
 *
 * ASSET LOCK — doc truoc khi sua file nay.
 * Curi la mascot thuong hieu chinh thuc. Trong repo nay TUYET DOI khong duoc
 * thay the bang: SVG/CSS tu ve, emoji cu, icon cu tu thu vien, mot con cu
 * "gan giong", anh crop tho tu screenshot tham chieu, hay bat ky hinh nao
 * khong phai file 3D canonical. Dieu do cung ap dung cho illustration truong
 * hoc va cho wordmark "Cursus" (khong tu dung lai chu).
 *
 * Vi cac file that CHUA co trong repo, component nay ve mot
 * DEVELOPMENT PLACEHOLDER trung tinh — mot khung ke net dut ghi ro ten file
 * con thieu va kich thuoc can co. Placeholder co chu dich la trong "chua
 * xong", de khong ai nham no voi thiet ke hoan chinh. No khong mo phong
 * Curi duoi bat ky hinh thuc nao.
 *
 * Khi asset that duoc dat vao `public/brand/` dung ten trong
 * `public/brand/README.md`, <img> tai duoc va placeholder bien mat — khong
 * can sua mot dong code nao.
 */

/** true khi <img> khong tai/decode duoc, tuc file chua ton tai. */
function useAssetProbe(src) {
  const [missing, setMissing] = useState(false);
  return [missing, () => setMissing(true), src];
}

function Placeholder({ file, width, height, label, style, className }) {
  const { lang } = useLanguage();
  return (
    <span
      className={`brand-asset-missing${className ? ` ${className}` : ''}`}
      style={{ ...style, aspectRatio: width && height ? `${width} / ${height}` : undefined }}
      // Bao cho trinh doc man hinh biet day la cho trong dang cho asset, chu
      // khong phai noi dung that.
      role="img"
      aria-label={
        lang === 'vi'
          ? `Thiếu asset: ${file}`
          : `Missing asset: ${file}`
      }
    >
      <span className="brand-asset-missing__tag">
        {lang === 'vi' ? 'THIẾU ASSET' : 'ASSET MISSING'}
      </span>
      <code className="brand-asset-missing__file">{file}</code>
      {width && height && (
        <span className="brand-asset-missing__dim">{width}×{height}px · PNG/WebP alpha</span>
      )}
      {label && <span className="brand-asset-missing__note">{label}</span>}
    </span>
  );
}

/**
 * @param {string} file   ten file trong public/brand/, vd "curi-student.png"
 * @param {string} alt    ten co nghia; de rong => trang tri (aria-hidden)
 * @param {number} width  kich thuoc goc de bao ty le o cho placeholder
 */
export default function BrandAsset({
  file,
  alt = '',
  width,
  height,
  className = '',
  style,
  note,
}) {
  const [missing, markMissing, src] = useAssetProbe(`/brand/${file}`);

  if (missing) {
    return (
      <Placeholder file={file} width={width} height={height} label={note}
        style={style} className={className} />
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      aria-hidden={alt ? undefined : 'true'}
      className={className}
      style={style}
      draggable="false"
      // object-fit: contain theo contract — khong bao gio cover, khong crop
      // bang CSS, khong ep width+height lam meo ty le.
      onError={markMissing}
    />
  );
}
