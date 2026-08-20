#include "core/Server.h"
#include <iostream>
#include <string>

int main(int argc, char ** argv) {
    try {
        int port = 8287; // Default port

        // Parse command-line arguments for --port
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if ((arg == "--port" || arg == "-p") && i + 1 < argc) {
                port = std::stoi(argv[i + 1]);
                i++; // Skip the next argument value
            } else if (arg.rfind("--port=", 0) == 0) {
                port = std::stoi(arg.substr(7));
            }
        }

        Server server;  
        server.loadResourcesAndRoutes();  
        server.listen(port);               
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
