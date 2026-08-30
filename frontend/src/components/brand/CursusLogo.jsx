import React from 'react';
import BrandAsset from './BrandAsset';

/**
 * Logo lockup chinh thuc: Curi + wordmark "Cursus" + tagline
 * "Plan · Do · Reflect", trong MOT file.
 *
 * KHONG dung lai wordmark bang HTML/SVG o day. Chu "Cursus" la mot phan cua
 * asset thuong hieu; go lai bang font he thong se tao ra mot phien ban logo
 * thu ba — dung dieu asset lock cam. Neu file chua co, BrandAsset ve khung
 * placeholder ghi ro ten file can bo sung.
 *
 * Be rong theo brand spec: 210px desktop, 180px tablet, 150px mobile (dat
 * trong cursus-brand.css). Duoi 140px dung rieng icon Curi thay vi thu nho
 * ca lockup.
 */
export default function CursusLogo({ className = '', alt = 'Cursus · Plan · Do · Reflect' }) {
  return (
    <BrandAsset
      file="cursus-logo-horizontal.png"
      alt={alt}
      width={840}
      height={288}
      className={className}
    />
  );
}
