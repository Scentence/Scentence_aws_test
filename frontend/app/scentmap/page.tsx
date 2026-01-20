export default function MapPage() {
    return (
        <div className="w-full h-screen bg-[#E5E5E5] flex items-center justify-center">
            <div className="bg-white p-8 rounded-2xl shadow-lg text-center">
                <h1 className="text-2xl font-bold mb-4">🗺️ 향수 관계맵</h1>
                <p className="text-gray-600">내 향수들의 취향 관계도를 시각적으로 확인하는 공간입니다.</p>
                <div className="mt-8 w-64 h-64 bg-gray-100 mx-auto rounded-full flex items-center justify-center">
                    <span className="text-gray-400">Map Visualization Area</span>
                </div>
            </div>
        </div>
    );
}