/**
 * Фоновое свечение на всю страницу.
 *
 * Раньше зелёная обложка обрывалась и дальше шёл ровный светлый фон — стык
 * читался как склейка двух разных сайтов. Теперь мягкие пятна тех же цветов
 * тянутся по всей длине страницы, а обложка растворяется в них снизу.
 *
 * Слой закреплён (`fixed`): при прокрутке пятна остаются на месте, поэтому
 * длина страницы не влияет на плотность фона.
 */
export function Ambience() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-paper" />

      <div className="float-a absolute -left-[18%] top-[8%] h-[62vh] w-[70vw] rounded-full bg-[radial-gradient(circle,rgba(147,168,69,0.30),transparent_62%)] blur-2xl" />
      <div className="float-b absolute -right-[14%] top-[24%] h-[70vh] w-[62vw] rounded-full bg-[radial-gradient(circle,rgba(109,140,62,0.26),transparent_64%)] blur-2xl" />
      <div className="float-c absolute left-[12%] bottom-[6%] h-[58vh] w-[66vw] rounded-full bg-[radial-gradient(circle,rgba(195,206,106,0.28),transparent_63%)] blur-2xl" />
      <div className="float-b absolute right-[6%] bottom-[18%] h-[46vh] w-[46vw] rounded-full bg-[radial-gradient(circle,rgba(244,241,210,0.55),transparent_60%)] blur-2xl" />
      <div className="float-a absolute left-[38%] top-[46%] h-[44vh] w-[44vw] rounded-full bg-[radial-gradient(circle,rgba(247,246,233,0.7),transparent_58%)] blur-2xl" />
    </div>
  );
}
