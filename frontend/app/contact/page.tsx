
export default function ContactPage() {
    return (
        <div className="w-full h-screen bg-[#E5E5E5] flex items-center justify-center">
            <div className="bg-white p-8 rounded-2xl shadow-lg max-w-md">
                <h1 className="text-2xl font-bold mb-6 text-center">📞 Contact Us</h1>
                <div className="space-y-4">
                    <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                        <h3 className="font-bold text-yellow-800">카카오 문의 채널</h3>
                        <p className="text-sm text-gray-700">SCENTENCE (검색)</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <h3 className="font-bold text-gray-800">이메일 문의</h3>
                        <p className="text-sm text-gray-700">5scompany@contact.com</p>
                    </div>
                </div>
            </div>
        </div>
    );
}