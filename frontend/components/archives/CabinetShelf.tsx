/* CabinetShelf.tsx (Refined Frame & Triangle) */
"use client";

interface MyPerfume {
    my_perfume_id: number;
    perfume_id: number;
    name: string;
    brand: string;
    image_url: string | null;
    status: string;
}

interface Props {
    perfume: MyPerfume;
    onSelect: (perfume: MyPerfume) => void;
}

export default function CabinetShelf({ perfume, onSelect }: Props) {
    // 상태별 색상 (삼각형)
    const cornerColor = perfume.status === 'HAVE' ? 'border-t-indigo-600' :
        perfume.status === 'WANT' ? 'border-t-rose-500' : 'border-t-gray-400';

    return (
        <div
            onClick={() => onSelect(perfume)}
            className="
        bg-white rounded-2xl relative group cursor-pointer
        border border-gray-100 hover:border-[#C5A55D]/50
        shadow-sm hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1
        flex flex-col h-full overflow-hidden p-3
      "
        >
            {/* 
        이미지 컨테이너 (Inner Box) 
        - 패딩을 줄여서 프레임 느낌 축소
        - 사진 모서리에 삼각형 배치
      */}
            <div className="w-full aspect-[4/5] relative bg-gray-50 rounded-lg overflow-hidden group-hover:bg-[#FFFCF5] transition-colors duration-500">

                {/* 모서리 삼각형 (Image Corner) */}
                <div
                    className={`
            absolute top-0 left-0 z-20 w-0 h-0 
            border-t-[32px] border-r-[32px] 
            border-r-transparent ${cornerColor}
            drop-shadow-sm opacity-90
          `}
                />

                {/* 이미지 (꽉 차게) */}
                <div className="absolute inset-0 p-4 flex items-center justify-center">
                    {perfume.image_url ? (
                        <img
                            src={perfume.image_url}
                            alt={perfume.name}
                            className="w-full h-full object-contain drop-shadow-md group-hover:scale-110 transition duration-500 will-change-transform mix-blend-multiply"
                        />
                    ) : (
                        <div className="text-gray-300 text-xs">No Image</div>
                    )}
                </div>
            </div>

            {/* 텍스트 정보 */}
            <div className="pt-3 pb-1 flex-1 flex flex-col justify-center px-1">
                <p className="text-gray-400 text-[10px] font-bold uppercase tracking-widest mb-1 truncate">
                    {perfume.brand}
                </p>
                <p className="text-gray-800 font-bold text-sm leading-snug line-clamp-2 group-hover:text-[#C5A55D] transition-colors">
                    {perfume.name}
                </p>
            </div>
        </div>
    );
}
