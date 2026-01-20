export default function ArchivesPage() {
    return (
        <div className="w-full h-screen bg-[#E5E5E5] flex items-center justify-center">
            <div className="bg-white p-8 rounded-2xl shadow-lg max-w-md text-center">
                <h1 className="text-2xl font-bold mb-4">📂 나만의 아카이브 (향수 옷장)</h1>
                <p className="text-gray-600">내가 저장한 향수와 추천받은 기록들이 이곳에 전시됩니다.</p>
                <div className="mt-6 space-x-2">
                    {/* 나중에 기능 구현 */}
                    <button className="px-4 py-2 bg-black text-white rounded-lg">향수 추가</button>
                    <button className="px-4 py-2 border border-gray-300 rounded-lg">삭제</button>
                </div>
            </div>
        </div>
    );
}