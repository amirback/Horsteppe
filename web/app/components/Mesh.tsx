/**
 * Органический зелёный фон с макета: крупные цветовые пятна под сильным
 * размытием, дающие «жидкий» градиент степи. Один SVG вместо картинки —
 * масштабируется без потерь и весит несколько килобайт.
 */
export function Mesh({ className = "" }: { className?: string }) {
  return (
    <div className={`absolute inset-0 overflow-hidden ${className}`} aria-hidden="true">
      <svg
        viewBox="0 0 1440 900"
        preserveAspectRatio="xMidYMid slice"
        className="mesh-drift h-full w-full"
      >
        <defs>
          <filter id="meshSoft" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="70" />
          </filter>
        </defs>

        <rect width="1440" height="900" fill="#3a6626" />

        <g filter="url(#meshSoft)">
          {/* верхний ряд: олива слева, жёлто-зелёный свет по центру, шалфей справа */}
          <ellipse cx="230" cy="185" rx="330" ry="215" fill="#93ab42" />
          <ellipse cx="590" cy="150" rx="310" ry="205" fill="#cbd36c" />
          <ellipse cx="930" cy="150" rx="290" ry="190" fill="#6f9040" />

          {/* тёмные массы: они и создают рисунок волны */}
          <ellipse cx="1490" cy="60" rx="270" ry="215" fill="#17381b" />
          <ellipse cx="1450" cy="500" rx="310" ry="300" fill="#0c2711" />
          <ellipse cx="0" cy="540" rx="300" ry="330" fill="#091d0c" />
          <ellipse cx="140" cy="900" rx="360" ry="260" fill="#0b230d" />

          {/* тёмная змейка через центр */}
          <path
            d="M210 760 C 400 570, 570 390, 780 425 C 960 455, 1020 670, 1200 810"
            stroke="#0e2a0f"
            strokeWidth="230"
            strokeLinecap="round"
            fill="none"
          />

          {/* светлая лента — главный акцент макета */}
          <path
            d="M120 400 C 380 275, 545 545, 690 645 C 790 715, 845 760, 905 800"
            stroke="#f2f0d0"
            strokeWidth="175"
            strokeLinecap="round"
            fill="none"
          />

          {/* нижнее световое пятно и зелень справа снизу */}
          <ellipse cx="820" cy="855" rx="330" ry="200" fill="#f6f3d6" />
          <ellipse cx="628" cy="512" rx="200" ry="145" fill="#eceabe" />
          <ellipse cx="1280" cy="860" rx="300" ry="190" fill="#41702b" />
        </g>
      </svg>
    </div>
  );
}
